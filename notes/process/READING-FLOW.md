# How people actually read this site

Written 15 September 2026, after walking the live site as a resident. The finding was
that the pages are good and the paths between them assume the reader already knows the
map. This document is the map we expect a reader to follow, so that every page can be
built to hand them to the next one — and so that nobody has to read a page in full for
the site to have worked.

**The premise: nobody reads a 45-minute page.** Word counts from the build of
15 September (`fy28/dist`, body text only, at 230 words a minute):

| page | words | at a reading pace |
|---|---:|---:|
| /one-big-report | 17,128 | 74 min |
| /crisis | 10,488 | 45 min |
| /straight-answers | 8,602 | 37 min |
| /bend-the-curve | 8,483 | 36 min |
| /what-solved-requires | 7,683 | 33 min |
| /the-paraprofessionals | 4,804 | 20 min |
| /homes-and-taxes | 3,531 | 15 min |
| /overrides | 3,051 | 13 min |
| /the-money | 2,476 | 10 min |
| / (front page) | 1,576 | 6 min |

A resident gives a page they did not come for about **eight seconds** before deciding
whether to scroll, and a page they did come for a few minutes. So the design assumption
is: **every page is read top-down and abandoned at some depth, and the depth is short.**
What a reader takes away is whatever was above the point they stopped. The long pages are
not the problem — they are the working, and the reason anything here is checkable — but
each one has to deliver its conclusion before the reader leaves, and hand them onward at
that point rather than at the bottom.

The term for the shape is **progressive disclosure**: the conclusion first, the
supporting layer under it, the full working under that, with a way out at every layer.
Rule 7b in CLAUDE.md is the same rule for one page; this document is it for the site.

---

## Three readers, three paths

None of them came for "the budget". Each came with one question.

### 1. The parent — *is my kid's thing on the list, and when is the vote?*

Arrives from a Facebook group or a text, usually on a phone, usually in the evening.

    front page
      → This week in town (the board card: tonight, Zoom link, last time)
      → the board page (/boards/school-committee)
      → the last meeting's short version (/meeting-minutes/...)
      → maybe the video at the timestamp
      → maybe the budget feed's "warned about" column

**Where they stop:** the meeting page's short version. Five bullets with timestamps is
the whole visit. They will never see the crisis page and that is fine.

**What each page must hand them:**
- The front page: tonight's meeting with the join link, above the fold on a phone.
- The board page: "next meeting" first, then "last time" with the one-sentence headline.
- The meeting page: the short version, then votes. Everything below is for reader 3.
- The budget feed: which programmes have been *warned about* — that is the parent's
  question, and it is the column on the right of "the cuts".

### 2. The taxpayer — *how much more will I pay, and is the town wasting money?*

Arrives from a mailer, a letter to the editor, or an override argument. Sceptical.

    front page
      → Budget Crisis (the number is on the door: "$633k short, projected")
      → the short version: five cards, the wedge
      → "What it means for your tax bill" / "What an override would cost"   ← the row under the wedge
      → What the town can do (/solutions)
      → stops

**Where they stop:** after the wedge, if the page has given them the number and the
override cost by then. If the page opens with a disclaimer, they stop *there*, having
concluded the numbers are made up.

**What each page must hand them:**
- The front page: the projected gap on the crisis door, labelled as a projection.
- The crisis page: the number in the first sentence with its label beside it; the
  caveats at the foot. The two objections (state aid, development) *after* the wedge —
  they are answers to questions this reader has not asked yet, and read as an argument
  starting before they have said anything.
- The row under the wedge: the tax bill, the override, the solutions. This is the exit
  this reader takes, and it did not exist before 15 September.
- /solutions: the table — what, closes, who decides, what it costs somebody — is the
  page. The rate argument below it is for reader 3.

### 3. The board member — *what is the number now, what are the options, what did the other board do?*

Arrives on purpose, weekly, often the night before a meeting. Already knows the vocabulary.

    front page
      → the budget feed (the gap, the cuts, the proposals, the override track)
      → the other boards' last meetings (votes, transfers)
      → /solutions: the options with who-decides and what-it-costs
      → the working: /bend-the-curve, /what-solved-requires, /build-your-own-budget
      → the reports, by subject, when a specific line is on the agenda

**Where they stop:** they don't, but they skim. This reader uses the site as a
reference and needs *findability* more than narrative: the header bar, the breadcrumb,
real links they can open in tabs and send to colleagues, page titles that name the page
in the browser tab.

**What each page must hand them:**
- The budget feed: the state of every track in one screen; "not yet" rows with the
  usual date, so they know what is coming.
- /solutions: the rate section ("why most of the table does not end it") and the ranked
  swing per line. This is the part written for them.
- Every report: the conclusion cards first (rule 7b), the chart, the raw. They will
  read the raw when the line is on tonight's agenda.
- Every link an `<a href>`, so that "open in new tab" and "copy link" work. This was
  not true before 15 September: the door cards, the header tabs and the thirty-two
  report cards on /the-money were buttons.

---

## The handoffs, as a graph

The rule is that every page has one *next* for each reader that reaches it, placed at
the point that reader is likely to stop — not at the bottom.

    /                 → crisis (taxpayer) · solutions (board) · this-week (parent) · feed (board)
    /crisis           → solutions · homes-and-taxes · overrides        [row under the wedge]
                      → the working (#the-working)                     [same row, for those who doubt]
    /solutions        → bend-the-curve · what-solved-requires · build-your-own-budget   [foot]
    /the-money        → the two revenue pages · the reports by subject · what-we-cannot-answer
    /this-week        → boards/<board> · meeting-minutes/<meeting> · budget-feed
    /boards/<board>   → next meeting's agenda · last meeting's minutes · votes
    /meeting-minutes  → the video at the second · the board page · the budget feed
    /budget-feed      → the meeting each row cites · solutions (when "the cuts" fills)

Where a page has no next for one of its readers, that is a gap in this graph and it
should be added here first and built second.

---

## What this rules out

- **A caveat above the thing.** It goes at the foot, linked from the top. A reader who
  needs it will look for it; a reader who does not will leave when they meet it first.
- **A door without scent.** "The budget feed" was our name for a thing no resident has
  heard of. A door says what is behind it in words the reader already has.
- **Five equal doors.** The reader cannot rank them, so we do: the crisis first and
  heavier, the answer beside it, the plumbing quiet.
- **A button where a link belongs.** Navigation is an anchor. Always. `lib/nav.tsx`.
- **The same `<title>` on every page.** Each page names itself in the tab; a reader with
  three open should be able to tell them apart. `lib/title.ts`.
- **Assuming the reader reaches the bottom.** They do not. Whatever is load-bearing goes
  above the first place they are likely to stop, and the exit goes with it.
