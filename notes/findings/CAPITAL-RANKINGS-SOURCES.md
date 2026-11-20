# Capital planning rankings: what the archive holds, by cycle

20 November 2026. Inventory only; nothing here is on a page. Written for the year-over-year
capital rankings page (TJ: *"i want to see the ranking year over year"*).

| money for | ranking source held | extracted? |
|---|---|---|
| FY2023 | `town-budget/docs/a75-fy23-capital-plan-presentation-pdf.pdf` p9: TM priority #, CPC priority #, Collins pts per project; the deck says the CPC prioritised 31 requests | no |
| FY2024 | `town-budget/docs/a194-fy24-composite-project-ranking-by-capital-planning-committee-pdf.pdf` (Collins score, five member ranks, their average) and `a195` TM deck p18 "not included" list (TM / CPC / Collins) | no (only the field's line, in `capital-plan-field-lines.csv`) |
| FY2025 | `budget-workbooks/finance-committee/fy25-budget/capital-planning-committee-files/fy25-capital-requests-by-department-final-cpc.xlsx`, sheet Ordered: column A (unheaded) composite order, E dept priority, H Collins; and `1504` TM deck p22 | 35 rows, `capital-requests.csv` version `fy25-ranked-inputs` |
| FY2026 | FY2025 annual report p138, two CPC-ranked options (1-21, 1-17). The CPC's 25-item list approved 16 Dec 2024 is NOT held | `capital-program-options.csv` |
| FY2027 | `fy27-capital-planning-committee-priorities-list-version-2-menard.xlsx`, `fy27-capital-plan.xlsx`, Article 13 p6: 22 ranked, funded yes/no | `capital-plan-fy27.csv` |

Department decks: FY24 `a196`-`a199`, `361`, police PDF; FY25 `a203`-`a209`; FY27
`budget-workbooks/finance-committee/fy27-budget/capital-planning/dept-requests/`. Whether each
deck prints the department's own priority order has not been checked.

Two disagreements already known: the field in FY2024 is CPC priority 21 on `a195` p18 and
about 19th by average rank on `a194`; the schools' FY2025 deck says rank 7 in the PDF and 9 on
one PPTX slide.

TJ sent a records request on 20 November 2026 for five years of department priority lists,
the final priorities given to the Town Manager, and the scoring sheets. A delivery goes
through the private gate (CLAUDE.md rule 13e) before any of it is used.

## What TJ wants the page to do (20 November 2026)

> *"i want to clik into a FY and see what was asked for by department, then what was
> prioritized, in rank order. with data to show breakdowns and percents by department of who
> got prioritized"*

So: a hub of fiscal years, and one page per FY (hub and spoke). Each FY page shows, in this
order: what each department asked for (count and dollars); the ranked list in rank order, with
every ranking scheme the year's documents print side by side; and each department's share of
the requests set against its share of what was prioritised or funded, in percent. The
"funded / not included" line comes from the document, never from a cutoff we choose. A year
whose ranking is not held still gets a page that says so, with the gap registered.
