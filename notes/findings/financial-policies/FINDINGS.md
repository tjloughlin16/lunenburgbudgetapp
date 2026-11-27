---
status: reference
genlock: T-5ABAV
---
# Financial policies: what was established, 27 November 2026

What the policy report rests on, and what checking it turned up. The figures are not typed here:
they come from `scripts/financial_policies_data.py` and are rendered by
`scripts/build_financial_policies.py` (four draft topic pages at `/town-reserves/<id>` and
`sources/analyses/financial-policies.md`, both unlisted). `scripts/verify_financial_policies.py`
recomputes the headline figures by its own route.

## Documents added to the archive for this

- The Select Board's *Policies and Procedures* (town DocumentCenter 506): Article III, sections
  3.01-3.08, are the financial policies in force.
- Three DLS Municipal Databank exports of 25 November 2026, every municipality: stabilization as a
  share of budget, certified free cash as a share of budget, and general fund debt service.
- The DLS draft manual (April 2024) was already held.

## Established, by checking

1. **The 3 December 2026 Finance Committee agenda lists 22 policy titles, not 20.** They match the
   DLS manual's table of contents title for title (10 planning, 12 operations). The agenda attaches
   no policy text. The generator asserts the match from both documents.
2. **The manual's stabilization balances are the previous 30 June's**, to the dollar, in all four
   years of its table (pdf page 31). An earlier note set its FY2024 figure against the annual
   report's FY2024 and called the two different; they are one year apart, not in conflict.
3. **FY2025 general stabilization has two printed figures.** The annual report's trust table
   (unaudited) and treasurer's cash list print one; the state databank carries the same. The FY2025
   audit's stabilization note prints a higher one. Neither is chosen. A `money-gaps.csv` row asks
   for the reconciliation.
4. **The databank's general stabilization equals the annual reports' only from FY2017.** Before
   that its figure is larger. For FY2014 and FY2015 it equals general plus zoning incentive, to the
   dollar. The trend starts at FY2017 for that reason.
5. **Today's stabilization section quotes two caps the statute no longer contains**, and asks two
   thirds to spend from any stabilization fund. The current text of M.G.L. c. 40, §5B asks a
   majority for a special-purpose fund and two thirds for the general fund (read 27 November 2026).
6. **The draft states the yearly stabilization deposit two ways**: 0.25% in its summary table (pdf
   p. 28) and 0.3% in its text (pdf p. 30).
7. **The OPEB schedule in the FY2025 audit re-adds**: every row identity across nine years, the
   funded ratio as trust over liability, and the contribution deficiency.

## Corrections to the earlier research notes

Checked meeting by meeting (`sources/data/financial-policy-record.csv` is the result: roles only,
minutes against captions marked):

- Several statements attributed to minutes are in captions only. That covers the "estimated near
  three million, collected over four" remark (FinCom 12 September 2024) and the "roughly five
  percent" remark (Select Board 16 March 2026). No figure heard only in captions is given on the
  pages.
- The "piggy bank" remark (FinCom 3 April 2025) was public comment, not a committee member. There
  were two 6-0 no-action votes that night, on free cash to the general and to the special purpose
  stabilization funds.
- The 2014 Finance Committee vote (4-0) recommended the policies; the Board of Selectmen adopted
  them 5-0.

## Not established

- Whether the December draft is the April 2024 manual unchanged.
- Any OPEB actuarial valuation after the two held (FY2017, FY2018).
- Where the reserve fund's $50,000 rule came from.
- The free cash certification as of 1 July 2026 (not in the databank on 25 November 2026).
- The DLS free cash guidance page on mass.gov refused an automated fetch. The state's
  recommendation is therefore quoted from the DLS manual drafted for Lunenburg, which the archive
  holds.
