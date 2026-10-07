# The PEC health insurance agreements: what we hold, what the record says exists

6 October 2026. The Public Employee Committee (PEC) agreement under M.G.L. c.32B §19 sets the
Town's health insurance plans, the premium split, and retiree benefits for every bargaining
unit. The timeline is generated on the health options page from `sources/data/pec-history.csv`.

## It is a SERIES, not one document

The Select Board said so itself, 12 April 2022: *"We enter into agreements with the PEC every
so many years and the current one ends June 30th."* What the record shows:

| date | instrument | held? | where the record names it |
|---|---|---|---|
| 16 Jun 2008 | the base agreement, term 1 Jul 2008 – 30 Jun 2012, "continue thereafter until the new agreement is reached" | **held**: `sources/contracts/pdf/pec-agreement-2008.pdf` | union contracts; the document itself |
| 14 May 2013 | an amendment | **not held** | Select Board minutes, 11 Mar 2014 |
| 4 Jun 2013 | an agreement reported "to last until June 30, 2016" (whether it is the 14 May amendment is not established) | **not held** | Select Board minutes, 4 Jun 2013 |
| 11 Mar 2014 | the 2013 amendment amended: paragraphs 7 and 8 struck, a $51,406 mitigation fund distributed | **not held** | Select Board minutes, 11 Mar 2014 |
| 1 Jul 2022 | a new agreement: Blue Select added, Part B moved from a percentage to a flat amount, an opt-out requested | **not held** | Select Board minutes, 12 Apr 2022, item 4 |
| 1 Jul 2026 – 30 Jun 2029 | a Memorandum of Agreements that "amends the current in-force health insurance agreement" | **held** with Attachment A (four active-plan summaries) and Attachment B (opt-out policy) | the documents themselves |

All of it came from Julie Belliveau, Human Resources Director, by email on 5 and 6 October 2026.
Her words on the attachments: *"The Benefit Summaries are Attachment A, and the Opt-Out Policy
is Attachment B."* She also wrote that she was *"working on producing a complete, current
Agreement"*: a consolidated version (amended and restated). It does not exist yet, as far as
we know.

## Decision: model from the FY27 memorandum

TJ, 6 October 2026: *"ok lets just use it then."* The memorandum restates every money term
in full (plans, 75/25 active and Managed Blue for Seniors, 50/50 Medex, $96/month Part B, the
$3,000/$6,000 opt-out, and the term), so nothing the model uses depends on an instrument we
lack.

## What is NOT established, and why the missing ones still matter

- **Which instrument the FY27 memo amends.** It doesn't say. The July 2022 agreement is the
  likeliest; that is an inference from the dates, not a statement anywhere.
- **Whether 2022 replaced 2008 or amended it.** Only the 2022 document would show.
- **The history of the split.** 80% → 75% on the HMO from 1 July 2011 is in the 2008 agreement
  and the 1 March 2011 minutes. Any move between 2011 and 2026 would be in the missing
  instruments. Each one is a dated point on that line, which is why they are worth asking for
  eventually.
- **The procedural terms the memo carries over unrestated:** eligibility, and how retirees and
  spouses are defined. The 2008 copy has a handwritten margin note on p4: *"retiree & spouse
  or just retiree?"*
- **The two Medicare plans' benefits.** Attachment A covers the four active plans only. The
  Managed Blue for Seniors and Medex summaries are a separate gap in `money-gaps.csv`.

## 2008 against FY27, from the two documents only (rule 7: no causes)

| | 2008 | FY27 |
|---|---|---|
| Office visit | $15 | $20 PCP / $45 specialist |
| Deductible | none stated | $500/$1,000; $2,000/$4,000 on the HSA plan |
| Town share, active plans | PPO 75%; HMO 80% → 75% from 1 Jul 2011 | 75% on all |
| Medicare Part B | 75% of the premium | $96 a month |
| Opt-out | none | $3,000 individual / $6,000 family |
