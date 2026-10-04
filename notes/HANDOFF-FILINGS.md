# TWO FILINGS, READY TO SEND — queued 4 October 2026, TJ sends 5 October

**Status: WRITTEN, NOT SENT.** Both drafts are finished. TJ fills the placeholders and
sends them himself. Nothing here is automated and nothing should be sent by an agent.

## The two, and they go to DIFFERENT places

| | about | goes to | draft |
|---|---|---|---|
| **1. OML complaint** | School Committee minutes not created/posted | **the TOWN** — Laura Brzozoski, Chair, School Committee; copy to `openmeeting@mass.gov` | `notes/outbound/COMPLAINT-oml-school-committee-minutes.md` |
| **2. Records appeal** | the 4 Sep MUNIS request to the Town Manager, unanswered | **the STATE** — `pre@sec.state.ma.us`, Supervisor of Records | `notes/outbound/APPEAL-supervisor-of-records-town-accountant.md` |

**These were drafted the wrong way round first and corrected.** Open Meeting Law
complaints (c.30A §23) go to the public body FIRST and then the AG's Division of Open
Government — never the Secretary of State. Public records appeals (c.66 §10A, 950 CMR
32.08) go to the Secretary of State's Public Records Division. Do not swap them back.

## Before sending

- **Both:** fill `[name] · [address] · [email] · [phone]`. The Public Records Division
  needs a real mailing address.
- **#1 must go on the AG's official form** — mass.gov/how-to/file-an-open-meeting-law-complaint.
  The draft supplies the two narrative blocks to paste in. Attach
  `notes/outbound/REQUEST-school-committee-minutes.pdf`.
- **#2:** attach `notes/outbound/sent-2026-09/RECORDS-REQUEST-TOWN-ACCOUNTANT.pdf` —
  the copy as actually sent, sha256 in that folder's `MANIFEST.json`.
- **Neither has been rendered to PDF.** Offered, not done.

## THE ONE UNRESOLVED THING — check before sending #2

**The 4 September request never cites M.G.L. c.66 §10, never says "public records
request", and opens "Hello again."** Massachusetts needs no magic words (950 CMR
32.06), but a Town that wants to wriggle will say it read as a collegial ask.

Two routes, TJ's choice:
- send the appeal as drafted; or
- send the Town Manager one line — *"treating my 4 September request as a public records
  request under c.66 §10, please respond within ten business days"* — and appeal cleanly
  if that lapses. Slower, much harder to deflect.

The 8 September minutes request has no such problem; it cites the statute in its opening line.

**Also unconfirmed:** `answered_on` is empty in `notes/reference/records-requests.csv` and
nothing has landed in `sources/town-ledgers/` since 4 September — newest MUNIS material is
still period 09, from the June request. But an email reply that produced no document would
not show in the repo. **TJ should confirm he had no reply at all before claiming silence.**

## The figures, and how they were established

Read live off the Town's own AgendaCenter on **4 October 2026**, not off our crawl
(rule 13c), by querying `AgendaCenter/Search?CIDs=24` per year and counting distinct
`ViewFile/Minutes/_<MMDDYYYY>-<id>` links in the returned HTML:

| calendar year | SC meetings announced | minutes posted | not posted |
|---|---:|---:|---:|
| 2022 | 33 | **0** | 33 |
| 2024 | 36 | 27 | 9 |
| 2025 | 46 | 30 | 16 |
| 2026 (to 1 Oct) | 24 | 14 | 10 |

- **Zero of the 35 minutes requested on 8 September have been posted.**
- Newest SC minutes on the Town's site: **24 June 2026**.
- Eight meetings announced since: 15 and 29 Jul, 26 Aug, 2, 9, 16 and 25 Sep, 1 Oct 2026.
  Three of those post-date the request. Arrears went 35 → 38 while it sat unanswered.
- Deadline arithmetic, computed not guessed: the 4 Sep request's ten business days expire
  **21 September 2026** (Labor Day, 7 Sep, excluded) — nine business days overdue at 4 Oct.

**NOT ESTABLISHED:** that minutes for these meetings were never written. c.30A §22
requires minutes to exist and be available on request, not to be online. The complaint
says this, and it must keep saying it.

## After sending

Add a row to `notes/reference/records-requests.csv` for each — not done yet, because
neither has a sent date.
