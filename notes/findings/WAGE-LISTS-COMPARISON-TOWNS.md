# Do the comparison districts publish teachers' gross pay?

**A SURVEY, first 19 October 2026 (six districts), extended the same day to every
comparison district.** The question behind it: Lunenburg's teacher pay distribution
(`/school-spending-history/teachers-on-the-scale`) comes from the town's own annual report,
which prints every town AND school employee's calendar-year gross pay by name. Can the same
picture -- each teacher's gross pay as a share of their OWN district's master's top step --
be built for the districts Lunenburg is compared with?

The two sets (`sources/data/comparison-sets.csv`): **the district's comparison districts**
(Nashoba, Groton-Dunstable, Ashburnham-Westminster, Shrewsbury, Uxbridge, Maynard, Wachusett,
Ayer Shirley, Hudson, Tyngsborough, Harvard) and **this project's six** (Ashburnham-Westminster,
Ayer Shirley, Groton-Dunstable, North Middlesex, Monty Tech, plus Lunenburg). Fitchburg and
Leominster were checked briefly.

Method: each member town's most recent annual reports (and a prior year where the latest had
nothing), the district's own site, and for some towns the Massachusetts State Library's
archive of town reports (archives.lib.state.ma.us). PDFs were downloaded and their text
searched page by page for earnings, wages paid, salaries and wages, remuneration, W-2, gross
pay and payroll; image-only pages were listed and the suspect ones looked at. **A "no" below
means not found in the places listed -- rule 13c: a search that finds nothing is a statement
about the search.**

## The result

| district | set | list found? | usable for teachers? | measured |
|---|---|---|---|---|
| Harvard | district's | **yes**, 2025 town report pp. 228-231, period not printed | **yes** -- its own TEACHER section | **on its own scale** |
| Ashburnham-Westminster | both | **yes**, the district's FY2025 list reprinted in Ashburnham's 2025 report pp. 136-146 | **yes** -- primary job title | dollar quartiles only: FY2025 schedule not held |
| Tyngsborough | district's | **yes**, "2022 Gross Wage Report", the latest the town posts | **yes** -- a position column with a school code | dollar quartiles only: FY2022-FY2023 schedule not held |
| Hudson | district's | yes, "School Wages 2025" in the 2025 town report pp. 285-293 | **no** -- name and amount only | -- |
| Maynard | district's | yes, "School Wages for Calendar Year 202*" in the 2025 report pp. 171-175 | **no** -- name and amount only | -- |
| Uxbridge | district's | yes, "CALENDAR YEAR 2024 SCHEDULE OF EMPLOYEE WAGES" in the FY2024 report pp. 154-162 | **no** -- town and school in one list, no title | -- |
| Shrewsbury | district's | no | -- | -- |
| Nashoba | district's | no | -- | -- |
| Wachusett | district's | no | -- | -- |
| Groton-Dunstable | both | no | -- | -- |
| Ayer Shirley | both | no | -- | -- |
| North Middlesex | project's | no | -- | -- |
| Monty Tech | project's | no | -- | -- |
| Fitchburg, Leominster | (brief) | no | -- | -- |

**Hudson, Maynard and Uxbridge publish lists that cannot be used.** With no job title, a
teacher cannot be told from a custodian, a substitute or an aide, and any rule over the
amounts alone (say, "everyone paid over $60,000") would select by the very quantity being
measured. They are refused, not guessed.

**Regional districts pay their own staff**, and none of the regional districts here
(Nashoba, Wachusett, Groton-Dunstable, Ayer Shirley, North Middlesex, Monty Tech) was found
to publish an earnings list, nor any member town to reprint one -- A-W is the one exception.
That the district rather than the town is the employer is the likely reason, and it is a
hypothesis: no document says it. **What would settle all of them is a records request** to each
district's payroll office for calendar-2025 gross earnings (W-2 Box 5) by employee with
position title -- counts only would do.

## Where each was looked for

### Read and used

- **Harvard.** harvard-ma.gov/Archive/ViewFile/Item/463 ("2025 Harvard Full Report -
  Website.pdf"). Contents: "Employee Earnings Report (Town/School) 218". PDF pp. 224-227
  town earnings by department; pp. 228-231 "SCHOOL EMPLOYEE EARNINGS REPORT", split SCHOOL-
  NON-TEACHER and TEACHER, each with a DEPT TOTAL. Period not printed.
- **Ashburnham-Westminster.** ma-ashburnham.civicplus.com/ArchiveCenter/ViewFile/Item/231
  ("2025 Annual Town Report (Final).pdf"), pp. 136-146, "Earnings In Excess of $500 7/1/24 -
  6/30/25", by name and PRIMARY JOB TITLE. Westminster's 2025 report
  (westminster-ma.gov/DocumentCenter/View/7230) reprints the same list. Schedules held:
  FY2017-FY2019 (DESE filing) and FY2026-FY2028 (`ashburnham-westminster-teachers-2025-2028.pdf`)
  -- neither covers FY2025.
- **Tyngsborough.** tyngsboroughma.gov/Archive.aspx?ADID=88 ("2022 Gross Wage Report
  (PDF).pdf"), archive category "Accounting Wage Reports" (2010-2022; nothing later listed).
  One spreadsheet printed across two runs of pages: pp. 1-13 Department and Name, pp. 14-26
  Position, SR, Munis and Total, row for row. The PDF prints no period or title line; "2022"
  is the archive's title and the filename. What SR and Munis mean is not stated; Total equals
  SR plus Munis on every row. Positions carry a school code (TES, TMS, THS, ECC, DW). Schedules
  held: FY2019-FY2021 (the DESE filing, effective 1 September 2018 to 31 August 2021) and
  FY2025-FY2027 -- neither covers 2022. The 2024 and 2025 town reports
  (DocumentCenter/View/2693, /3334) print no list. NOT CHECKED: the Document Center's
  financial-documents folder (DocumentCenter/Index/140), which loads by JavaScript and could
  hold a later wage report.

### A list, but no job titles

- **Hudson.** townofhudson.org/Archive.aspx?ADID=274 ("Annual Report 2025 final.pdf"),
  "Wage/Vendor Reporting": "Town Wages 2025" pp. 280-285, "School Wages 2025" pp. 285-293;
  calendar 2025 per the Treasurer's page. Name and one amount; no totals. The 2024 report
  (ADID=238) is the same.
- **Maynard.** townofmaynard-ma.gov/Archive.aspx?ADID=454 ("2025 ANNUAL TOWN REPORT FINAL
  5-1-26.pdf"): "Town Wages for Calendar Year 2025*" pp. 169-171, "School Wages for Calendar
  Year 202*" pp. 171-175 (the last digit is cut off on the page). Name and amount; no totals.
  2024 (ADID=371) the same.
- **Uxbridge.** uxbridge-ma.gov/DocumentCenter/View/6110/FY-2024 ("FY 2024.pdf"), pp. 154-162,
  one alphabetical list of town and school employees, table body an embedded image. The FY2025
  report is posted only as a flipbook (online.fliphtml5.com/zuzsu/mett/) with no PDF, NOT read.

### No list found

- **Shrewsbury.** 2025 town report (shrewsburyma.gov/Archive.aspx?ADID=1800, 486 pp, digital):
  no earnings section. 2024 (ADID=1695) is image-only; its contents page lists no wage
  schedule. 2023 (ADID=1651) image-only, not read.
- **Nashoba** (Bolton, Lancaster, Stow). Bolton 2025 (bolton-ma.gov/DocumentCenter/View/5458)
  and 2024 print "W-2 SALARIES AND WAGES (Box 5)", names and amounts with no department --
  town W-2s; the district W-2s its own staff, so teachers are almost certainly absent (an
  inference: the list has no column to prove it). Lancaster 2025 and 2024
  (ci.lancaster.ma.us/ArchiveCenter/ViewFile/Item/169, /168): none. Stow 2024 and 2023
  (stow-ma.gov/ArchiveCenter/ViewFile/Item/113, /112): none. nrsd.net refuses scripted
  fetches (a JavaScript challenge), not browsed.
- **Wachusett** (Holden, Paxton, Princeton, Rutland, Sterling). Sterling 2025 prints "GROSS
  WAGES - CALENDAR YEAR 2025" and Paxton 2025 a "TOWN PAYROLL REPORT", both town departments
  only. Holden 2025 and 2024, Rutland FY2025 (the Wachusett section is narrative), Princeton
  2025: none. wrsd.net budget pages: none.
- **Groton-Dunstable.** Groton 2025, 2024, 2023, 2017 (portal.grotonma.gov/storage/Town_Reports/):
  none. Dunstable 2025 and 2024: none; the district's section is narrative. gdrsd.org refuses
  scripted fetches, not browsed.
- **Ayer Shirley.** Ayer 2025, 2024, 2022: "Town Salaries and Wages" by job title, no names,
  town departments only. Shirley FY2025, 2024, 2023, 2022: "Town of Shirley Payroll", names,
  town only. asrsd.org: certified budgets only.
- **North Middlesex.** Pepperell 2024, 2023, 2022; Townsend 2024, 2023; Ashby 2025, 2024, 2023:
  none. nmrsd.org: budgets, audits, union contracts.
- **Monty Tech.** montytech.net business office: budgets only. A State Library full-text
  search of member-town reports found no reprint of its payroll; Templeton FY2024's earnings
  list is town only.
- **Leominster.** leominster.opencheck.net is a vendor checkbook, not a payroll. FY2024 city
  report: none.
- **Fitchburg.** No city or school payroll publication found.

## What this means for the work

- **One district is placed on its own scale: Harvard.** Two more (A-W, Tyngsborough) have
  usable lists and want only the salary schedule for the list's year; that is the cheapest
  next step, and it is registered in `sources/data/money-gaps.csv`.
- **The periods differ and are never mixed silently.** Lunenburg's list is calendar 2025;
  Harvard's prints no period; A-W's is fiscal 2025 and only earnings over $500; Tyngsborough's
  is 2022 with no period printed.
