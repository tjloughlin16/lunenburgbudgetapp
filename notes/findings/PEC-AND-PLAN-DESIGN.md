# Does §19 put plan design into bargaining? A claim, checked

**19 September 2026.** A resident posted the claim below in the Lunenburg budget group.
TJ asked for it to be checked against what this project holds, and for the answer and its
sources to be kept somewhere they can be pointed at later. This is that file.

The companion is `notes/findings/MA-MUNICIPAL-HEALTH-INSURANCE.md`, researched 18
September 2026, which is where the statute reading lives. Nothing here supersedes it; this
adds two documents it did not have.

---

## 1. The claim, verbatim

> "Saying this here because you looked at the law... Lunenburg enacted section 19 of the
> health insurance law, giving the PEC full bargaining power. This means that we just
> don't bargain over the premium split, but also plan design. This also means the town
> can't just say we need to change this (like they do in other towns), but have to go into
> full negotiations for any plan design change."

Three separable assertions:

| # | assertion | verdict |
|---|---|---|
| A | Lunenburg accepted §19 and has a PEC | **supported**, and now sourced |
| B | the premium split is bargained, not imposed | **correct** |
| C | therefore plan design requires full negotiation | **not correct as reasoning**; the conclusion may still hold for a reason the claim does not give |

---

## 2. What is established, and from where

**The split is bargained.** M.G.L. c.32B §21(f): *"The panel shall not impose any change
to contribution ratios."* Read from the statute page, not a summary —
<https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIV/Chapter32B/Section21>.
The Group Insurance Commission says the same in its own words (§5 below): *"The Commission
does not determine premium contribution ratios, which are a subject of collective
bargaining."*

**Plan design is not, under §§21–22.** The 2011 municipal health reform moved plan design
OUT of bargaining and left the split at the table. Under §§21–22 the Select Board may raise
copays, deductibles and tiers up to the GIC benchmark **with no Town Meeting vote**: 30 days
with the PEC, then a three-person panel decides in 10 days, binding, with employee
mitigation capped at 25% of first-year savings.
`sources/data/health-insurance-law.csv`, the §§21–22 row · `MA-MUNICIPAL-HEALTH-INSURANCE.md:39`

**Having a §19 PEC does not block §§21–22.** The PEC is who the town negotiates with during
those 30 days. §19 and §§21–23 are not alternatives.

**The PEC agreement exists and is dated 16 June 2008.** This is new, and it is the first
time the date has been sourced to a document rather than asserted. Town of Lunenburg
**Clerical Union Agreement FY2023–2026, Article 21 §1**:

> "The Town agrees to provide health and life insurance in accordance with the PEC
> (Public Employees Committee) Agreement dated June 16, 2008 (attached)."

<https://www.lunenburgma.gov/DocumentCenter/View/364/Fiscal-Year-2023-to-2026-Clerical-Union-Agreement-PDF>

**And it is NOT attached.** Checked page by page: all 35 pages carry extracted text, so
nothing is a hidden scan, and the document runs Articles 1–32 then three attachments —
A (Wage Schedule, pp31–33), B (Reclassification Request Form, p34), C (Compensatory Time
Procedure, p35). The word "attached" is doing no work.

---

## 3. What is NOT established

- **How and when §19 was accepted.** `MA-MUNICIPAL-HEALTH-INSURANCE.md:74` says "accepted
  2008 (the minutes say Town Meeting; §19(a) as written says selectmen — unresolved)" and
  **names no document**. The clerical contract dates the AGREEMENT to 16 June 2008; it does
  not say when the town accepted the section. Those are different events.
- **Whether Lunenburg ever accepted §§21–23.** Searched all **477 Town Meeting articles,
  FY2011–FY2025** (`sources/data/town-meeting-votes.csv`): no article accepts §19, §21, §22
  or §23. The only c.32B acceptance in fifteen years is **§20, the OPEB trust, FY2024
  Article 22**. Acceptance could predate FY2011, which is where that record begins.
  **This is the hinge.** If the town has not accepted §§21–23, the poster's conclusion is
  right in practice even though the reasoning is wrong.
- **What is in the PEC agreement.** Nobody outside the negotiation can read it. It fixes
  the 75/25 split and the terms.

---

## 4. The response as posted

Written to be checkable rather than to win. Every statutory claim carries a link; every
Lunenburg-specific claim either names its document or sits in the can't-confirm list.

> You're right that we're under §19 — Lunenburg went the PEC route, so it's coalition
> bargaining rather than unit by unit.
>
> And you're right about the split. §21(f): "The panel shall not impose any change to
> contribution ratios." Between 75% and the 50% floor that's negotiated, and nobody can
> impose it.
>
> Plan design is where I'd push back. The 2011 reform did the opposite of what you'd
> expect — it moved plan design out of bargaining and left the split at the table. Under
> §§21–22 the Select Board can raise copays, deductibles and tiers up to the GIC benchmark
> with no Town Meeting vote: 30 days with the PEC, then a three-person panel decides in 10
> days, binding. Employee mitigation is capped at 25% of first-year savings.
>
> Having §19 doesn't block that. The PEC is who the town sits across from during those 30
> days.
>
> For what it's worth on how we buy it: Lunenburg is fully insured through the MIIA Health
> Benefits Trust, a joint purchase under §12 — that's from the town's FY25 Budget Message,
> the 26 August 2025 joint minutes, and the 9 February 2021 Select Board minutes. Not
> self-insured; the DLS Self-Insured Health Trust Funds report has no rows for us.
>
> Three things I can't confirm and would genuinely like to see:
> 1. When and how we accepted §19 — I've seen 2008 referenced but haven't found the vote.
> 2. Whether we've ever accepted §§21–23.
> 3. Our PEC agreement itself — it isn't published anywhere I can find.

---

## 5. The GIC bulletin, and the thing it unlocks

**Administrative Bulletin 23-01, Guidance Regarding PEC Agreements**, Group Insurance
Commission, issued under c.32B §11.
<https://www.mass.gov/administrative-bulletin/23-01-guidance-regarding-pec-agreements>

**How our copy reached us, stated plainly (rule 12).** mass.gov refuses this project's
fetches — HTTP 403 with a bot-protection reference, to `curl` and to the assistant's
fetcher alike. The text below was **pasted by TJ from his browser on 19 September 2026**.
It has not been byte-verified against the publisher and should be treated as a
transcription until it is.

What it settles:

- **The split is bargained.** *"The Commission does not determine premium contribution
  ratios, which are a subject of collective bargaining."*
- **Benefits are not — where the GIC provides them.** §19(f): *"...the manner and method of
  payment, schedule of benefits, eligibility requirements, choice of health insurance
  Carriers, and each Carrier's Product offerings. These matters are not subject to
  collective bargaining."* **Lunenburg is MIIA, not GIC**, so this does not govern us
  directly; the §19(g) discussion does, because it covers plans *"whether provided through
  the Commission or through other municipal arrangements."*
- **What changed in 2023.** The GIC rescinded its 2008 guidance that contribution ratios
  could differ only by plan TYPE. A PEC agreement may now set a percentage per specific
  plan — but all employees in a plan get the same percentage, and differentiation by date
  of hire, bargaining unit, employment status or individual/family coverage is prohibited.
  The employer must pay at least 50%.
- **It does not mention §§21–23 at all.** So it does not settle the hinge in §3.

**THE LINE THAT MATTERS MOST**, and the reason this bulletin was worth chasing:

> "The GIC reminds municipalities that it must be provided PEC agreements to the
> Commission under 805 CMR 801. Additionally, the Municipal Employer shall notify the
> Commission of any change to Municipal Insureds' premium contribution ratios no later
> than March 1st. Changes to contribution ratios shall be effective July 1st."

**There is a second custodian.** We have been treating the PEC agreement as unobtainable
because the town does not publish it. A state agency is required to hold it — and to hold a
notification every time the split changes, which is a HISTORY of the split and not just its
current value. That is a public records request to the Commonwealth rather than to the
town.

**One transcription note.** This sentence reads as a drafting error in the source and
should be quoted, never paraphrased: *"A PEC agreement **may** set a premium contribution
percentage for each specific insurance plan... However, PEC agreements are **not
prohibited** from doing so."* The two halves say the same thing, so the "However" contrasts
with nothing; one clause was probably meant to read *not required*.

---

## 6. What to ask for

1. **The PEC Agreement dated 16 June 2008**, from the **Group Insurance Commission**,
   citing 805 CMR 801. Second-best: from the Town, which names it in every union contract.
2. **Every contribution-ratio notification the GIC holds for Lunenburg** — the March 1
   filings. This is the split, year by year, from a custodian outside the town.
3. **The Town Meeting or Select Board vote accepting §19**, and any vote accepting
   §§21–23. This is the one that decides whether the claim above is wrong or accidentally
   right.

---

## 7. What this changed in the archive

Nothing yet. `health-insurance-law.csv` still rests on our own reading of the statute
pages and does not cite the bulletin; the bulletin is not ingested — `state-dls` is the
wrong agency and there is no `state-gic` folder, and a fourteenth top-level folder is a
decision about the archive rather than a place to put a delivery. The clerical and
firefighters' union agreements are fetched but not ingested either: `sources/contracts/`
is the right home and **nothing watches the pages those come from** — the nine contracts
there were pulled by hand on 20 August 2026 and two of them carry provenance nobody has
been able to re-check since.
