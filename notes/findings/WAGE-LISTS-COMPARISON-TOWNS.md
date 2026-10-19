# Do the comparison districts' towns print employee gross wages?

**A SURVEY, 19 October 2026. Nothing has been downloaded or ingested.** The question
behind it: Lunenburg's teacher pay distribution (`/school-spending-history/teachers-on-the-scale`)
comes from the town's own annual report, which prints every town AND school employee's
calendar-year gross pay by name. Could the same be built for the five other districts this
project compares?

Method: each town's most recent annual report, read from the town's own site (text layer
plus the contents page; pages that are only images were NOT read). So a "no" below means
*not in the readable text of that report* -- rule 13c: a search that finds nothing is a
statement about the search. Older years were not checked for the towns marked no.

| district | town | report checked | address | names + gross pay? | school staff in it? | what was seen |
|---|---|---|---|---|---|---|
| Harvard | Harvard | 2025 | harvard-ma.gov/Archive/ViewFile/Item/463 | **yes** | **yes, separate section** | Contents: "Employee Earnings Report (Town/School) 218". PDF pp. 224-227 town earnings by department; pp. 228-231 "SCHOOL EMPLOYEE EARNINGS REPORT", split SCHOOL- NON-TEACHER and TEACHER. Period not seen on the pages. |
| Groton-Dunstable | Groton | 2025 (2022 also) | portal.grotonma.gov/storage/Town_Reports/2025_Annual_Report.pdf | no | -- | Only budget wage lines; the district's section is narrative. |
| Groton-Dunstable | Dunstable | 2024 | dunstable-ma.gov/select-board/files/2024-town-report | no | -- | No wage section in the contents, Treasurer or Accountant reports. 31 of 156 pages are images, not read. |
| Leominster | Leominster (city) | FY2024 | leominster-ma.gov/Archive/ViewFile/Item/351 | no | -- | The report is the Comptroller's report and audited statements. The city links an Open Checkbook (leominster.opencheck.net) -- not opened. |
| North Middlesex | Pepperell | 2024 | town.pepperell.ma.us/DocumentCenter/View/9842/2024-Annual-Town-Report | no | -- | No wage headings; 36 image pages not read. |
| North Middlesex | Townsend | 2024 | Townsend annual town report 2024 (cms3.revize.com, "updated 4.10.2025") | no | -- | Budget lines only, and an HR note that 245 individuals were on the town payroll. |
| North Middlesex | Ashby | 2025 | ci.ashby.ma.us annual reports page (Google Drive file) | no | -- | Budget lines only. |
| Ayer Shirley | Ayer | 2024 | ayer.ma.us/Archive/ViewFile/Item/88 | **by job title, no names** | no | "Town Salaries and Wages", PDF pp. 14-19: position and amount, town departments only. |
| Ayer Shirley | Shirley | FY2025 | shirley-ma.gov/Archive/ViewFile/Item/305 | **yes** | no | "Town of Shirley Payroll 2025", pp. 95-98, ending "Wages Paid in CY 2025". Town staff only. |
| Fitchburg | Fitchburg (city) | -- | fitchburgma.gov | not determined | not determined | No city annual report or payroll listing found before the search was cut short. |
| Ashburnham-Westminster | Ashburnham | 2025 | ma-ashburnham.civicplus.com/ArchiveCenter/ViewFile/Item/231 | **yes** | **yes -- the regional district's own list** | Town "Employee Earnings" (printed pp. 94-96). Printed pp. 137-147 reprint the district's "Earnings In Excess of $500 7/1/24 - 6/30/25", teachers included. |
| Ashburnham-Westminster | Westminster | 2025 | westminster-ma.gov/DocumentCenter/View/7230/Annual-Town-Report-2025 | **yes** | **yes -- the same district list** | "2025 Aggregate Employee Remuneration" (printed pp. 288-291), town staff; the school section reprints the district list. |

## What this means for the work

- **Two districts could be built the same way:** Harvard (its school earnings report splits
  TEACHER out by itself) and Ashburnham-Westminster (the district's own list, reprinted in
  both member towns' reports). Each would need its own roster or title to identify
  teachers -- Harvard's split does that already.
- **The periods differ, and must never be mixed silently.** Lunenburg's list is a calendar
  year; Ashburnham-Westminster's district list is a FISCAL year (1 July - 30 June) and only
  lists earnings over $500; Harvard's period was not seen.
- **North Middlesex, Groton-Dunstable and Ayer Shirley staff are paid by the regional
  district, not the member towns**, so a town report would not carry them even if it
  printed a list. Whether those districts publish an earnings list themselves was NOT
  checked.
- **Leominster and Fitchburg**: no list in the reports seen; Leominster's Open Checkbook is
  the next place to look.

The gap this leaves is registered in `sources/data/money-gaps.csv` ("Do the other five
districts' teachers sit as high on their salary schedules as Lunenburg's?").
