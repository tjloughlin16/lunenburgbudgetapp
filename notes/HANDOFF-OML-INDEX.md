# Design: the Open Meeting Law, predigested and indexed

Written 8 October 2026. Approved in principle by TJ the same day. Build after the full
determinations download (`fetch_oml_determinations.py --all`, started 8 Oct ~19:00) finishes.

TJ: *"we need a way to quickly try to apply OML and all determinations for the meetings.
Reading them all for each meeting won't work for sure."* -- *"we should also predigest the
determinations and laws and create fast indexes that could be used to find things."*

## The shape

Read everything ONCE, expensively and carefully. Then every meeting review LOOKS THINGS UP
and reads only the handful of rulings that bear on its points (~$1 a meeting, as now).

## 1. The law, cut into rule units (no model)

The statute (c.30A ss.18-25), 940 CMR 29.00, the AG's guide and checklists, split into
numbered units -- one requirement each (e.g. `c30a-20(b)` notice 48 hours; `c30a-21(a)(1)`
executive session purpose 1 + notice to the individual discussed; `940cmr29.03(1)(b)`
topics sufficiently specific). Each unit: id, verbatim text, source document, section,
and the ISSUE it belongs to (below). Built by script from the ingested text; verbatim is
asserted against the source, as everywhere else.

## 2. Every determination, digested once

Per letter, one structured digest:
- determination number, date, public body, BODY TYPE (school committee, select board,
  planning board, ...), the portal's Violation field;
- each ALLEGATION addressed: the issue (from the taxonomy), the AG's holding (violation /
  no violation / not reached), and the KEY PASSAGE quoted verbatim;
- remedy ordered, if any;
- determinations it CITES (regex, no model).

The citation list and metadata are free. The issue/holding/key-passage digest needs a model:
the cheapest one (haiku), ~4,000 letters, ~$40-100 API-equivalent total (~10-20% of a week),
run as a paced batch over several days through the same governor as the minutes backlog,
quotes checked verbatim against the letter or dropped -- exactly the extractor's rule.

## 3. The issue taxonomy (one table, one place)

notice timing - notice content / topic specificity - acronyms and jargon - topics not on the
notice / discussion beyond a topic - votes and roll calls - executive session: purposes 1-10,
procedure, minutes of executive session, release of executive session minutes - open-session
minutes content and approval timing - remote participation - public access and recording -
deliberation outside a meeting (quorum emails, serial communications) - complaint
procedure - remedies. Every rule unit and every digested allegation carries one or more.

## 4. The fast indexes (local, rebuilt from the digests; derived, like lunenburg.db)

- **FTS5** over rule units, digest key passages, and full letter text (`--corpus law`).
- **issue -> rulings**: for each issue, its determinations ranked by how often LATER letters
  cite them (the AG's own "leading cases") and by recency; filterable by body type and holding.
- **citation graph**: who cites whom, so a reader can follow a line of reasoning.
- **body-type filter**: "school committee + executive session purpose 1 + violation".

## 5. The review, two steps

1. Find candidate points in the meeting record (as now).
2. For each point: look up its issue -> the 3-5 leading rulings + the best text matches for
   the specific facts -> a second, small call confirms or downgrades the point, quoting the
   rule unit and the AG's own words. Each numbered point on the page then cites them.

A ruling is how the AG read the law in ANOTHER case. The point's status still reflects only
what THIS meeting's record shows; "violation" is still never said.

## Decided, 8 October 2026

TJ, told the digest is ~$80 API-equivalent (~16% of a week): *"Let's just ingest them. Don't
process them for now. We have meeting minutes that are more important."* So: the letters are
DOWNLOADED and SEARCHABLE (full text, `--corpus law`); sections 1, 3, 4 (rule units, taxonomy,
indexes, citation graph -- all model-free) may be built; section 2's model digest WAITS.

TJ, the same evening: *"We'll build a process identical to meeting minutes processing to do
the determinations. But later."* So when it is built, the digest runs exactly as the minutes
backlog does -- `process_meeting.py`'s shape: newest first, resumable, one step per letter
saved as it succeeds, the usage governor (`--until-usage`, session and weekly caps, the
output guard matching every paid call to its file). Not a separate one-off batch.
