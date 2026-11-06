# Email request, August 2025 — Parks & Recreation

## Where it came from

**Obtained from the Town of Lunenburg in answer to an emailed request by TJ Loughlin, who runs
this project**, sent 7 August 2025 to the Parks office, subject *Parks Information Request*. It
asked for revenue, cost, users, fees, property, maintenance and staffing per programme. It did
not cite the public records law, so it is an informal request, not a request under M.G.L. c. 66
§ 10. This note called it a records request, with the requester unnamed, until 5 November 2026,
when TJ supplied the thread, published at TJ's word as
`correspondence/2025-08-07-parks-information-request-thread.pdf`.

Christopher Ruth, Facilities Director, answered in two parts:

- **26 August 2025:** five attachments, *"the reports that contain the data you requested"*.
- **10 September 2025:** `Membership_Sales_Report_2025_08-29.pdf`, after TJ asked on 29 August
  for the Town Beach registrations, which the first set did not include.

There is no URL for any of it: none was published, and asking was the only route.

## What arrived, under which name, and where it is filed

Filed by what each one IS, not by the request (the archive layout's second rule):

| publisher's filename | our copy | what it is | sha256 |
|---|---|---|---|
| `Ytd_Budget_Report_20250815103019671.pdf` | `../expenses/glytdbud-expense-fy2024-p13-gf-parks.pdf` | MUNIS year-to-date budget report, FY2024, Parks & Recreation (departments 16501 salaries and 16502 expenses), with journal detail — every warrant, invoice and vendor. Two pages, image only: no text layer. | `551f5abd194ed05de71719928ac820d91916949da4a9be5092b1072a91fcab3a` |
| `Lunenburg Parks & Recreation_ Management System.pdf` | `parks-program-financials-fy2025-myrec.pdf` | MyRec *Program Sales Report*, 1 July 2024 – 30 June 2025: registrations and fees by programme, resident and non-resident, with a printed totals row. | `d37d6d14553123ab4e6f578835c44747cd1df17affe38a593ebd380f8b859333` |
| `Membership_Sales_Report_2025_08-29.pdf` | `parks-membership-sales-fy2025-myrec.pdf` | MyRec *Membership Sales Report*, same year: beach passes sold, resident and non-resident, with a printed totals row. | `c93147feab5f0160676a16d2bb933843a228973b62c14c5f16daf1dc739a6106` |
| `Parks Offerings.pdf` | `parks-program-offerings-fy2025-myrec.pdf` | MyRec programme catalogue for the year, 32 pages: every programme's description, sessions and fee as the public saw it. | `416df29be572e3074f63198a1710938eacad9bf8292c5f105ca013147b069c24` |
| `Landscaping Costs.pdf` | `../purchase-orders/po-closed-fy2025-parks-grounds-bid.pdf` | A contractor's bid sheet for municipal grounds maintenance, year one from 1 July 2024, priced per park (Fitzgerald, McNally, Marshall, Memorial, Town Beach, Wallis). A bid, not an invoice. | `ea3d724fe3427571df7e53227ba73c09b4177d03f08a1d91cee1a965383751ab` |
| `Swim Lesson Fees 2024.eml` | `../../correspondence/2024-03-01-parks-beach-and-swim-fees.txt` | An internal town email of 1 March 2024 recording the beach pass and swim lesson fees the Parks Commission voted that night. Headers and body kept; the transport headers dropped. | — |

## The period in the MUNIS report's filename is inferred, and this is the only place that says so

The report's own title block is not on either page — the scan starts at the column
headings. The journal runs to 30 June 2024 `GEN` entries and the file was printed on
15 August 2025, a year after the close, so `p13` (the year-end period) is the reading;
`p12` is possible. The filename has to carry a period and this is the one it carries.

## What is evidence and what is not (rule 13a)

- The MUNIS report and the two MyRec sales reports are **system printouts**: accounting
  and registration systems produced the figures, and each MyRec report foots to a totals
  row it prints itself. `scripts/extract_parks_myrec.py` writes both to
  `sources/data/parks-myrec-sales-fy2025.csv` and refuses to if a column stops tying.
- **MyRec is not the town's books.** It records registrations and the fees attached to
  them; what reached fund 1500 (Park Revolving) or the general fund is on the town's
  reports, and the two are not reconciled here. In FY2025 MyRec recorded $38,955.50 of
  programme fees and $8,828.00 of beach passes.
- The bid sheet is a vendor's offer, and the email is a statement of a vote — both
  `stated`, each carrying the authority of whoever wrote it.
- The MUNIS report has no text layer. Nothing has been extracted from it. Its totals line prints
  a grand total of $1,022,611.97 revised, far above the two Parks departments it lists. Mr Ruth
  explained why on 29 August 2025: *"When the report was initially run it had the facilities
  budget above it and totaled the 2 budgets together."* So that total is not a Parks figure.
- Also from Mr Ruth, stated rather than shown: lines with a warrant comment (`WARRANT-23P24 RUN-1
  TOWN OF`) *"are employee pay checks"*; `Salaries Programming`, $5,000, is *"a line item used for
  recreation programming, it is used for various programs depending on the year"*.

## What would settle what these do not

The FY2025 special-revenue report (fund 1500's receipts and spending for the year the
MyRec reports cover), and the fund's journal detail — the same report the archive holds for
fund 1301. Registered in `sources/data/money-gaps.csv`.
