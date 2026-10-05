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

## What the AG's form itself says (read off the 2025 form, 5 October 2026)

- A municipal body: file with the CHAIR **AND the MUNICIPAL CLERK**. Both. Mail, email or hand.
- The body meets on it and answers in writing within 14 business days, copying the AG.
- To the AG only after waiting 30 days, at `openmeeting@state.ma.us` -- not `mass.gov`.
  The Division will not review a complaint reaching it more than 90 days after the violation.
- Field limits: description 3,000 characters, remedy 500. FORM-TEXT.txt fits both.

## Before sending

- **Both:** fill `[name] · [address] · [email] · [phone]`. The Public Records Division
  needs a real mailing address.
- **#1 must go on the AG's official form** — mass.gov/how-to/file-an-open-meeting-law-complaint.
  Paste from `COMPLAINT-...-FORM-TEXT.txt`; attach the Gmail thread (8, 9, 17 Sep) printed
  to PDF, NOT the unsent draft request.
- **#2:** attach `notes/outbound/sent-2026-09/RECORDS-REQUEST-TOWN-ACCOUNTANT.pdf` —
  the copy as actually sent, sha256 in that folder's `MANIFEST.json`.
- **Neither has been rendered to PDF.** Offered, not done.

## #2 REWRITTEN 5 October 2026 from the emails as sent -- and a #3

TJ pasted both threads. **The Town Manager DID acknowledge the MUNIS request**, on 14 Sep:
*"You are in the queue! Targeting Thu/Fri."* Follow-ups on 24 Sep and 2 Oct (the 2 Oct one
cc'd a fellow resident, not a Town official) went unanswered. The appeal now says exactly
that. The acknowledgement also answers the "collegial ask" worry below: the Town treated
it as a request to fill.

**#3, the PEC agreement**, `APPEAL-supervisor-of-records-pec-agreement.md`: asked 19 Sep
(a Saturday) of the Town Manager and Dr. Fortuna, due 5 Oct, so **not appealable before
6 Oct**. On 5 Oct TJ told both he would be appealing.
**ANSWERED 5 Oct, the same day — the appeal is withdrawn and must not be sent.** Filed at
`sources/contracts/pdf/pec-agreement-fy27-fy29.pdf`; its Attachments A and B are blank.

## THE ONE UNRESOLVED THING — check before sending #2 (SUPERSEDED -- kept for the record)

**The 4 September request never cites M.G.L. c.66 §10, never says "public records
request", and opens "Hello again."** Massachusetts needs no magic words (950 CMR
32.06), but a Town that wants to wriggle will say it read as a collegial ask.

Two routes, TJ's choice:
- send the appeal as drafted; or
- send the Town Manager one line — *"treating my 4 September request as a public records
  request under c.66 §10, please respond within ten business days"* — and appeal cleanly
  if that lapses. Slower, much harder to deflect.

**CORRECTED 5 October 2026:** the 8 September minutes request as SENT (TJ pasted the Gmail
thread) cites no statute and opens "Can I please have a copy". The statute-citing text is
the DRAFT, `REQUEST-school-committee-minutes.md/.pdf`, which was never sent -- do not
attach it. It went to the Chair, listed 35 meetings with agenda links, and she replied on
9 Sep ("Liz is looking into this now") and 17 Sep. The sent list held 24 meetings for 2026;
the 27 counted on 5 October is those 24 plus 16 Sep, 25 Sep and 1 Oct.

**Also unconfirmed:** `answered_on` is empty in `notes/reference/records-requests.csv` and
nothing has landed in `sources/town-ledgers/` since 4 September — newest MUNIS material is
still period 09, from the June request. But an email reply that produced no document would
not show in the repo. **TJ should confirm he had no reply at all before claiming silence.**

## The Chair DID reply -- 17 September 2026

TJ pasted the thread on 5 October. The Chair wrote that she believed most of the minutes
were approved but not posted ("a disconnect with the posting"), that a staff member had to
verify which were approved, and that central office was busy without a finance director.
TJ replied he would take them in any form, unposted. Nothing has arrived since. The
complaint was rewritten to say exactly this, and its claim is now AVAILABILITY (§22(c)),
not non-approval -- her statement that they were approved is hers, not established.

## The figures, and how they were established

Read live off the Town's own AgendaCenter on **4 October 2026**, not off our crawl
(rule 13c), by querying `AgendaCenter/Search?CIDs=24` per year and counting distinct
`ViewFile/Minutes/_<MMDDYYYY>-<id>` links in the returned HTML:

| calendar year | SC meetings announced | minutes posted | not posted |
|---|---:|---:|---:|
| 2022 | 25 | **0** | 25 |
| 2023 | 43 | 9 | 34 |
| 2024 | 36 | 27 | 9 |
| 2025 | 46 | 30 | 16 |
| 2026 (to 1 Oct) | 27 | 14 | 13 |

**Re-counted 5 October 2026, by DISTINCT MEETING DATE.** The 4 October table mixed units:
2022's 33 was AgendaCenter ROWS, while 2024 and 2025 were dates. The same-date rows are
re-posts (amended and revised agendas, one meeting entered twice), so a date is the
meeting and rows overcount. 2026 read 24 on 4 October and is 27 by date; the cause of
that difference was not established. 2023 was missing and is now in.

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

**#1 FILED 5 October 2026, 1:41 PM** -- email to the Chair, cc the Town Clerk, form only.
Copy as sent, hashed: `notes/outbound/sent-2026-10/`. Register row
`2026-10-05-oml-complaint-school-committee-minutes`. Written response due **26 Oct**; to the
AG no earlier than **4 Nov**, no later than **30 Dec**. #2 is still unsent.

Add a row to `notes/reference/records-requests.csv` for each — not done yet, because
neither has a sent date.
