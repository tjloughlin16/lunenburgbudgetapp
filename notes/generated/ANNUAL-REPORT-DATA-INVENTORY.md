# What we hold from Lunenburg's annual town reports

Generated: 2026-11-07 by `scripts/build_annual_report_inventory.py`, from the database and the archive as they stood that day. Every count below is computed, not typed.

| | |
|---|---:|
| Annual reports held, 1959 to FY2025 | 68 documents |
| Pages of text read from them | 8,997 pages |
| Pages in the word search | 8,683 pages |
| Tables built from them | 111 tables |
| Rows in those tables | 157,481 rows |
| Of which: year-by-year series | 44 tables, 55,924 rows |
| Finding aids about the reports themselves | 9 tables |

Rows carry the edition and the page they were printed on, so a number can be checked against its page (except `report_new_growth_history`, which summarises across editions). The year-by-year series also quote the printed line.

## What you can do with it

- **Search the pages by word.** Any phrase, across 8,683 pages of all 68 editions, at `https://lunenburgbudgetproject.org/search`. Each hit links to that page of the original PDF.
- **Ask a question in SQL.** Every table below is in a public database. One web address runs a read-only query, for example `https://lunenburgbudgetproject.org/api/query?sql=SELECT edition, measure, value FROM series_fire_calls LIMIT 20`.
- **Follow a figure back to its page.** Rows carry `edition` and `page`; the original scanned report is at `https://lunenburgbudgetproject.org/docs/town-annual-reports/docs/<file>.pdf#page=N`.
- **Download it.** Every table is a CSV in the public repository (`https://github.com/tjloughlin16/lunenburgbudgetapp`), named in the tables below.
- **Compare across 60+ years.** The year-by-year series put the same measure from every edition in one table: fire calls, burials, enrolment, pay schedules, trust funds, permits.

## How it is stored

1. **The original reports**: 68 PDFs (867 MB), kept unchanged in a locked archive, each with its sha256 and the town's own address for it.
2. **The page text**: read from every page (by Amazon Textract for the scans), 21 MB of text, one file per report.
3. **The tables**: CSV files in git, the source of truth. Rows name their page; where a report prints its own total, the extract is checked against it.
4. **The database**: the CSVs are loaded into one SQLite database (`lunenburg.db`), copied online to Cloudflare D1 and queried at `/api/query`.
5. **The search index**: a second database holding the text of every page with a word index (SQLite FTS5), 8,683 annual-report pages, searched at `/api/search`.

Everything printed in the annual reports is public, names included.

## Every table, by subject

The grouping is ours, made for reading. *Editions* counts the reports a table has rows from; a series marks the editions that do not print the item in a separate coverage table.

### Money: budgets, spending, receipts and debt

39 tables, 58,857 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `report_appropriations` | APPROPRIATIONS as the annual reports print them — the largest extract here, 4,665 rows across sixteen years. | 1959–FY2025 | 67 | 27,799 |
| `annual_report_receipts` | Town REVENUE — every receipt line the annual reports print, by name and amount, per year. | 1959–2022 | 63 | 7,856 |
| `report_statement_of_payments` | The Treasurer's DETAILED STATEMENT OF PAYMENTS, July 1985 - June 1986, by department and object. | 1959–1986 | 28 | 4,670 |
| `special_revenue_funds` | Every fund OUTSIDE the general appropriation: balance brought forward, receipts, disbursements, balance carried forward. | 1992–FY2025 | 35 | 4,532 |
| `report_fund_balance_sheets` | One balance sheet PER FUND with a single amount column -- general fund liabilities, assets, fund balance and long-term debt; | 1959–1986 | 28 | 3,720 |
| `report_debt` | Outstanding DEBT and repayment schedules as the annual reports print them. | 1959–FY2025 | 58 | 3,533 |
| `report_capital_projects` | Capital project funds as the annual reports print them: appropriated, expended, encumbered and balance, per article. | 1999–FY2025 | 26 | 1,317 |
| `series_monty_tech_budgets` | What the Monty Tech reports print about the district's budget, member-town assessments, enrolment and grants, by year. | 1983–FY2025 | 26 | 862 |
| `report_school_budget_summary` | The School Committee's summary of the general appropriation by account series (1000 ADMINISTRATION ...): appropriation, amendment, spent and the coming year's request… | 1959–1985 | 27 | 660 |
| `series_treasurer_cash_investments` | Treasurer's cash investments. The Treasurer's Recapitulation of Revenue Cash Invested in the 1978, 1979 and 1980 reports: by half year, each bank and vehicle line with… | 1977–1980 | 4 | 553 |
| `report_treasurers_cash_reconciliation` | The Treasurer's cash ROLL-FORWARD for the fiscal year -- balance at the previous 30 June, receipts less investments transferred, disbursed less revenue cash invested,… | 1959–2008 | 47 | 545 |
| `series_receipts_fragments` | Receipts and payments fragments, 1985 and FY2023. | 1985–FY2023 | 35 | 341 |
| `series_capital_plan_holes` | What the capital plan listed, item by item, for the editions capital_plans does not hold. | 1996–FY2025 | 16 | 295 |
| `report_revenue_sharing` | The federal General Revenue Sharing fund's receipts by source and payments by purpose, fiscal 1986. | 1973–1986 | 14 | 291 |
| `series_revolving_fund_limits` | What spending limit town meeting voted for each revolving fund, year by year. | 1992–FY2025 | 34 | 221 |
| `report_fee_schedule` | Fee schedules adopted by town meeting vote -- the Sealer of Weights & Measures' fee per device class (2003, ATM May 3 2003 Article 24) and the Town Clerk's fees under… | 1964–2004 | 16 | 218 |
| `report_transitional_receipts` | The Treasurer's detailed statement of receipts for the 18-MONTH TRANSITIONAL YEAR, January 1, 1973 - June 30, 1974, in three period columns `Jan-Dec 1973 / Jan-Jun 1974… | 1974 | 1 | 197 |
| `report_treasurers_cash_calendar_year` | A SECOND Treasurer's reconciliation, for the CALENDAR year ended 31 December 1986, and its account list. | 1978–1986 | 9 | 191 |
| `report_warrant_article_amounts` | Per-project amounts printed inside a warrant article -- Article 8 of the 12 May 2001 Annual Town Meeting, a $41,190,000 Master Capital Facilities Plan of eight… | 1972–2006 | 9 | 178 |
| `report_auditors_cash_schedule` | The AUDITOR's own schedule of the Treasurer's cash and investments at the close -- balances by fund (opening and closing) and their composition by bank account. | 1983–1988 | 6 | 168 |
| `series_oneoff_finance` | Single-year finance tables with no series of their own: 1962 tax rate recap, 1981 assessment example, FY2019 revenue and changes, FY2024 fund balance roll-forward,… | 1962–FY2025 | 5 | 153 |
| `report_expenditure_shares` | The FY 1983 expenditure pie as PERCENTS, no dollars. | 1960–1983 | 9 | 104 |
| `report_vendor_payments` | Payments over $4,000 to one payee in fiscal 1986 (MGL c.40 s.4G), name and address as printed. | 1986 | 1 | 98 |
| `series_sewer_billing` | How many properties are connected and how much was billed and went delinquent. | 2007–FY2025 | 19 | 76 |
| `report_surplus_free_cash` | Analysis and comparison of surplus revenue and free cash, fiscal, and fiscal 1981 ESTIMATED. | 1965–1980 | 4 | 58 |
| `report_appropriations_supplement` | Page 60 of the FY2011 appropriations schedule, the page the generic extract first missed, read separately: one row per printed line with its program and the five money… | 2011 | 1 | 32 |
| `report_agency_funds` | Money the Town held for others at 30 June 1987 -- payroll withholdings, union dues, guarantee deposits. | 1987 | 1 | 26 |
| `report_committee_income_expenses` | Income and expenses of the 250th Anniversary / Old Home Week committee. | 1978 | 1 | 22 |
| `report_revenue_cash_invested` | The Treasurer's revenue cash invested and the interest it earned, by half-year (1974, with money borrowed and interest paid) or as totals for the fiscal year, the… | 1974–1980 | 4 | 21 |
| `report_financial_performance` | The Treasurer's nineteen-line comparison of financial performance data, FY 1975 - FY 1979 (taxes committed and outstanding, debt, valuation, cash invested, free cash,… | 1979 | 1 | 19 |
| `report_highway_accounts` | The Highway Superintendent's own appropriated / expenditures / balance for his accounts, to the dollar (fiscal 1995 by the schedule; | 1995 | 1 | 18 |
| `report_cash_management` | The State-required monthly cash management chart -- month-end cash on hand and in non-interest and interest-bearing accounts, fiscal 1981. | 1981 | 1 | 17 |
| `report_treasurers_then_and_now` | The Treasurer's comparison of the office's workload thirty years earlier against 1991 -- population, persons assessed, excise bills, persons on payroll, total receipts… | 1961–1991 | 2 | 16 |
| `report_treasurers_outlook` | The Treasurer's own projection for FY83 and an illustration of a hidden payroll cost. | 1981 | 1 | 14 |
| `report_capital_project_costs` | The School Building Addition Committee's cost of the new wing, work on the existing building and committee expense, to completion. | 1961 | 1 | 13 |
| `report_expenditure_history` | Population, school enrollment and town expenditures by category at five-year intervals, as the report prints them. | 1971 | 1 | 10 |
| `report_school_building_approved_costs` | The costs the School Building Assistance Commission APPROVED for the Jr.-Sr. | 1959 | 1 | 6 |
| `report_office_budget_cuts` | The Town Clerk / Tax Collector / Treasurer table FY 83 / FY 84 / DECREASE -- two budgets and the difference the office printed. | 1983 | 1 | 4 |
| `report_energy_use` | School fuel oil consumed (gallons, barrels) and degree days, 1972-73 to 1974-75. | 1976 | 1 | 3 |

CSV files: `sources/data/annual-report-receipts.csv`; `sources/data/report-agency-funds.csv`; `sources/data/report-appropriations.csv`; `sources/data/report-appropriations-supplement.csv`; `sources/data/report-auditors-cash-schedule.csv`; `sources/data/report-capital-project-costs.csv`; `sources/data/report-capital-projects.csv`; `sources/data/report-cash-management.csv`; `sources/data/report-committee-income-expenses.csv`; `sources/data/report-debt.csv`; `sources/data/report-energy-use.csv`; `sources/data/report-expenditure-history.csv`; `sources/data/report-expenditure-shares.csv`; `sources/data/report-fee-schedule.csv`; `sources/data/report-financial-performance.csv`; `sources/data/report-fund-balance-sheets.csv`; `sources/data/report-highway-accounts.csv`; `sources/data/report-office-budget-cuts.csv`; `sources/data/report-revenue-cash-invested.csv`; `sources/data/report-revenue-sharing.csv`; `sources/data/report-school-budget-summary.csv`; `sources/data/report-school-building-approved-costs.csv`; `sources/data/report-statement-of-payments.csv`; `sources/data/report-surplus-free-cash.csv`; `sources/data/report-transitional-receipts.csv`; `sources/data/report-treasurers-cash-calendar-year.csv`; `sources/data/report-treasurers-cash-reconciliation.csv`; `sources/data/report-treasurers-outlook.csv`; `sources/data/report-treasurers-then-and-now.csv`; `sources/data/report-vendor-payments.csv`; `sources/data/report-warrant-article-amounts.csv`; `sources/data/report-series/capital-plan-holes.csv`; `sources/data/report-series/monty-tech-budgets.csv`; `sources/data/report-series/oneoff-finance.csv`; `sources/data/report-series/receipts-fragments.csv`; `sources/data/report-series/revolving-fund-limits.csv`; `sources/data/report-series/sewer-billing.csv`; `sources/data/report-series/treasurer-cash-investments.csv`; `sources/data/special-revenue-funds.csv`.

### Taxes, valuation and assessments

9 tables, 4,074 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `series_tax_collection_holes` | What the Tax Collector's tables print by levy year for the annual report editions the other collection datasets do not hold. | 1961–FY2024 | 8 | 1,336 |
| `report_valuation` | Assessed property VALUATION by class, as the annual reports print it. | 1960–FY2019 | 37 | 1,029 |
| `series_pie_chart_shares` | Revenue and spending pie charts, 1983 and, and the growth chart. | 1959–FY2023 | 39 | 773 |
| `report_school_state_aid` | The School Committee's table of state aid by chapter (70, 71, 76, 766, 188) against the school appropriation, FY-85 to FY-87. | 1959–1986 | 27 | 378 |
| `report_new_growth_history` | New growth (added valuation, the prior-year rate, the revenue it added, new structures where printed), total assessed valuation and the tax rate, before FY2011, read… | 1985–2010 | 22 | 202 |
| `report_property_tax_exemptions` | The Board of Assessors' summary of property tax exemptions available, by statutory clause (17D, 22, 22E, 37A, 41A, 41C, 42, 43; | 1974–1991 | 18 | 179 |
| `report_tax_bill_breakdown` | The Board of Assessors' Breakdown of the Average Residential Tax Bill for the coming fiscal year (FY1996, FY1997): budgeted amount by town service under eight category… | 1995–1996 | 2 | 135 |
| `report_tax_collection_by_levy_year` | The Tax Collector's report by levy year -- committed, collected, abated, abatement rescinded, refunded, added to tax title, balance -- and betterments. | 1961–1962 | 2 | 39 |
| `report_per_capita_comparison` | Per capita expenditure and property tax per capita, fiscal year 1976, for Lunenburg against the Massachusetts and fifty-state averages (U.S. | 1978 | 1 | 3 |

CSV files: `sources/data/report-new-growth-history.csv`; `sources/data/report-per-capita-comparison.csv`; `sources/data/report-property-tax-exemptions.csv`; `sources/data/report-school-state-aid.csv`; `sources/data/report-tax-bill-breakdown.csv`; `sources/data/report-tax-collection-by-levy-year.csv`; `sources/data/report-valuation.csv`; `sources/data/report-series/pie-chart-shares.csv`; `sources/data/report-series/tax-collection-holes.csv`.

### Trust funds and investments

3 tables, 12,221 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `report_trust_funds` | Trust fund balances and activity as the annual reports print them. | 1959–FY2025 | 63 | 5,508 |
| `series_trust_fund_ledgers` | Trust fund balance and income ledgers. The Balances and Income ledgers of the trust fund pages: for each fund (cemetery perpetual care, worthy poor, library, sidewalks… | 1961–FY2019 | 41 | 5,017 |
| `series_trust_fund_holdings` | Trust fund holdings by bank. The Trust Fund Commission's Investment of Funds pages: for each trust fund (library, sidewalks and grounds, worthy poor, cemetery perpetual… | 1961–FY2025 | 29 | 1,696 |

CSV files: `sources/data/report-trust-funds.csv`; `sources/data/report-series/trust-fund-holdings.csv`; `sources/data/report-series/trust-fund-ledgers.csv`.

### Pay, staff and officials

16 tables, 36,636 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `staff_roster_entries` | PEOPLE — one row per name the town printed, per year, with the school, the page, the printed job title and our classification of it., 3,815 entries. | 1959–2025 | 63 | 12,278 |
| `report_gross_wages` | GROSS WAGES paid per named employee per year, as the annual reports print them. | 1995–FY2025 | 28 | 11,512 |
| `series_classification_schedules` | Town classification and salary schedules: class, step and printed rate. | 1966–FY2016 | 14 | 3,173 |
| `series_office_hours_directories` | Office hours and phone directories. Town office hours by office from the front matter of every edition, the telephone directories by subject and FY2012, the office… | 1959–FY2025 | 67 | 2,672 |
| `series_school_personnel_changes` | School personnel changes and roster detail. | 1959–FY2017 | 49 | 2,558 |
| `report_officials` | Names and offices of town officials as each annual report lists them. | 1961–FY2024 | 33 | 1,838 |
| `series_meeting_schedules_due_dates` | Meeting schedules and tax due dates. The front-of-book list of when and where each board meets, and the list of when real estate, excise and poll taxes and dog licences… | 1960–FY2018 | 58 | 697 |
| `series_official_lists` | Other named lists of officials. Name and rank or role as printed for people on lists town-roster-entries.csv and staff-roster-entries.csv do not hold: the Fire… | 1959–FY2025 | 45 | 461 |
| `report_school_staff_fte` | School Department staff in FTE by role and school, school year ending June 1986. | 1959–1986 | 28 | 450 |
| `series_staff_roster_pages` | School staff rosters: pages the staff-roster-entries reader did not load. | 1964–2007 | 10 | 345 |
| `report_proposed_salary_schedule` | The Personnel Committee's PROPOSED classification and salary schedule for a coming March or July. | 1966–1973 | 7 | 302 |
| `report_signatures` | Who signed each department's report in the annual reports, with the title they printed beside their name, attributed to the department by the town's own contents page. | 2012–2025 | 14 | 179 |
| `series_pay_grades_fy2011` | What grade or rate each town position carried in the years a classification plan is read here. | 1984–FY2015 | 3 | 98 |
| `report_classification_plan` | Schedule A's Classification Plan -- each town job class title with its POINT VALUE (the job-evaluation score) and GRADE, which keys into salary-schedule. | 2010 | 1 | 54 |
| `report_voted_pay_rates` | Police pay RATES by step voted at a special town meeting (1974 p83, 1976 p55), and hourly special-detail rates. | 1974–1976 | 2 | 12 |
| `report_school_staff_changes` | The School Committee's PROPOSED staff reductions and additions in the FY-78 request, with the dollar effect of each. | 1977 | 1 | 7 |

CSV files: `sources/data/report-classification-plan.csv`; `sources/data/report-gross-wages.csv`; `sources/data/report-officials.csv`; `sources/data/report-proposed-salary-schedule.csv`; `sources/data/report-school-staff-changes.csv`; `sources/data/report-school-staff-fte.csv`; `sources/data/report-signatures.csv`; `sources/data/report-voted-pay-rates.csv`; `sources/data/report-series/classification-schedules.csv`; `sources/data/report-series/meeting-schedules-due-dates.csv`; `sources/data/report-series/office-hours-directories.csv`; `sources/data/report-series/official-lists.csv`; `sources/data/report-series/pay-grades-fy2011.csv`; `sources/data/report-series/school-personnel-changes.csv`; `sources/data/report-series/staff-roster-pages.csv`; `sources/data/staff-roster-entries.csv`.

### Schools

16 tables, 25,553 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `series_school_enrolment_by_grade` | School enrolment by school and class. October 1 enrolment tables as printed: each classroom (grade, teacher, boys, girls, total) under its school with the printed… | 1959–2000 | 38 | 9,900 |
| `series_student_names_and_honors` | Named students: graduating classes, officers, prizes and recognition. | 1959–FY2024 | 56 | 6,073 |
| `series_monty_tech_lists` | Monty Tech lists and sports notes. Lists and counts from the Montachusett Regional Vocational Technical School district report: trades and programs offered (1967, 1969,… | 1967–FY2025 | 28 | 4,238 |
| `series_mcas_from_reports` | What the annual reports print of MCAS results, against the state where printed. | 1998–FY2025 | 27 | 1,142 |
| `report_school_special_accounts` | The School Department's Summary of Special Accounts FY 86 -- revolving, grant and article accounts. | 1959–1986 | 28 | 913 |
| `series_school_calendars` | School calendars. The school calendar the School Committee printed each year: term and event dates as printed text, the number of no-school days the calendar allows,… | 1959–FY2021 | 30 | 848 |
| `series_sped_indicators` | How many students the reports say received special education, against the state, and each state indicator printed. | 1976–FY2025 | 31 | 841 |
| `report_enrollment_mcas` | Enrollment counts and MCAS results as the annual reports print them. | 1987–FY2025 | 27 | 747 |
| `report_school_lunch` | The School Lunch Program report -- meals served by month (COUNTS), and the program's income, USDA reimbursements and expenditures by month (DOLLARS), with year summaries. | 1959–1979 | 21 | 668 |
| `report_monty_tech` | Figures for Montachusett Regional Vocational Technical School as the annual reports print them. | 1966–FY2017 | 2 | 79 |
| `report_special_education` | The Special Services report's statistics tables -- shares of students by disability type (district against state), and state indicators (dropout rate, educational… | 2008–2009 | 2 | 46 |
| `series_monty_tech_enrollment` | How many Lunenburg students attended Monty Tech, by the town list the reports print. | 1971–FY2017 | 18 | 19 |
| `placement_counts` | CHILDREN, not dollars. Students placed outside the district, split collaborative / day / residential, measured on 1 March each year from SIMS Report 7.. Carries its own… | 2011–2025 | 15 | 15 |
| `report_school_spending_shares` | The school dollar -- what the schools spent in 1971 by category and by kind (salaries, expenses, capital), with the percent of the total. | 1971 | 1 | 13 |
| `report_school_census_minors` | The registration and distribution of minors -- boys and girls by age band, and where they were enrolled. | 1967 | 1 | 10 |
| `series_enrolment_2006` | School enrolment by grade, 2006 gap. Grade-by-school enrolment tables as of October 1: this pass adds only the one 2006 page-36 cell (Grade 10, 10/02/06) that… | 2006 | 1 | 1 |

CSV files: `sources/data/placement-counts.csv`; `sources/data/report-enrollment-mcas.csv`; `sources/data/report-monty-tech.csv`; `sources/data/report-school-census-minors.csv`; `sources/data/report-school-lunch.csv`; `sources/data/report-school-special-accounts.csv`; `sources/data/report-school-spending-shares.csv`; `sources/data/report-special-education.csv`; `sources/data/report-series/enrolment-2006.csv`; `sources/data/report-series/mcas-from-reports.csv`; `sources/data/report-series/monty-tech-enrollment.csv`; `sources/data/report-series/monty-tech-lists.csv`; `sources/data/report-series/school-calendars.csv`; `sources/data/report-series/school-enrolment-by-grade.csv`; `sources/data/report-series/sped-indicators.csv`; `sources/data/report-series/student-names-and-honors.csv`.

### Elections, votes and by-laws

4 tables, 6,924 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `report_elections` | Election results as the annual reports print them: candidates, offices and vote counts in ordinal columns. | 1959–FY2025 | 42 | 3,863 |
| `series_ballot_questions_local` | How each local ballot question went, by precinct. | 1960–FY2025 | 35 | 1,761 |
| `series_bylaw_warrant_text` | By-law, zoning and warrant text. Fines, fees and dimensions printed in by-law, zoning and warrant text as figures with their unit (fines in dollars, yards, heights and… | 1959–FY2025 | 66 | 1,291 |
| `ballot_questions` | VOTES, not dollars — though each carries the amount at stake. | not dated | 0 | 9 |

CSV files: `sources/data/ballot-questions.csv`; `sources/data/report-elections.csv`; `sources/data/report-series/ballot-questions-local.csv`; `sources/data/report-series/bylaw-warrant-text.csv`.

### People and vital records

8 tables, 5,199 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `series_burials` | Burials in the town cemeteries, by name. The list of persons buried in the North and South Cemeteries that the Cemetery Commission (or Cemetery Department) report… | 1959–FY2025 | 66 | 2,448 |
| `report_vital_records` | Counts of births, marriages and deaths as the annual reports print them. | 1959–FY2025 | 30 | 2,311 |
| `series_town_nurse_visits` | Town nurse visits and clinics. The Town's own public health nurses' counts as the Health, Town Nurse and Town Nursing Service pages print them: nursing visits by kind,… | 1959–1976 | 18 | 169 |
| `series_births_census` | Births recorded and dated census populations printed in the reports: census lines, births, birth totals 1976 and. | 1959–FY2025 | 35 | 96 |
| `series_veterans_services` | How many veterans and families were aided and what was paid and reimbursed, in the years the reports print it. | 1959–FY2025 | 25 | 69 |
| `report_welfare_aid` | The Welfare Department's table -- persons aided or average case load (1959), expended, reimbursements from the State, Federal government, cities and towns, and net cost… | 1959–1967 | 7 | 53 |
| `series_coa_services` | How many Meals on Wheels meals and senior van rides the Council on Aging reports. | 1976–FY2019 | 18 | 40 |
| `report_veterans_services` | Veterans' Services case loads, amount expended and the half returned by the State. | 1964–1971 | 2 | 13 |

CSV files: `sources/data/report-veterans-services.csv`; `sources/data/report-vital-records.csv`; `sources/data/report-welfare-aid.csv`; `sources/data/report-series/births-census.csv`; `sources/data/report-series/burials.csv`; `sources/data/report-series/coa-services.csv`; `sources/data/report-series/town-nurse-visits.csv`; `sources/data/report-series/veterans-services.csv`.

### Public safety, permits and services

14 tables, 6,852 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `report_dept_activity` | Departmental activity tables — permits issued, inspections done, cases handled. | 1959–FY2025 | 49 | 2,264 |
| `series_nashoba_public_health` | What Nashoba reported doing for Lunenburg each year: inspections, tests, nursing visits, communicable disease cases. | 1959–FY2025 | 57 | 1,317 |
| `series_fire_calls` | How many calls the Fire Department reported each year, and in what categories, read from every annual report. | 1959–FY2025 | 67 | 926 |
| `series_building_activity` | How many permits the Building Department reports, by type. | 1963–FY2025 | 57 | 484 |
| `series_trade_permits` | Plumbing, gas and wiring permits, inspections and fees. | 1960–FY2022 | 63 | 465 |
| `series_town_facts` | What the reports print for population, registered voters, road miles and area over time. | 1959–FY2025 | 67 | 375 |
| `series_police_activity` | What the Police Department reports it handled each year. | 1959–FY2025 | 62 | 342 |
| `series_library_usage` | How much the library's reports say it was used each year. | 1959–FY2025 | 59 | 252 |
| `series_conservation_filings` | Conservation Commission filings, decisions, hearings and wetlands fees. | 1972–FY2025 | 53 | 248 |
| `series_cultural_council_grants` | Which applicants and projects the Cultural Council funded, and what total each year's report prints. | 1984–FY2024 | 16 | 87 |
| `report_vehicle_inventory` | Highway Department vehicles and equipment as of March 1996 -- year, make and model, mileage. | 1995 | 1 | 32 |
| `report_town_facts` | The town facts page -- county, area, road miles, census population, assessed valuation and tax rate, one fact per row, as printed. | 1959–1978 | 6 | 27 |
| `report_weights_measures` | The Inspector of Weights & Measures' table of devices adjusted, sealed, not sealed and condemned with the sealing fee per device, and the consumer and merchant savings… | 2010 | 1 | 23 |
| `report_library_service_values` | The library's own ESTIMATE of what its services were worth to residents (count used x a unit price the page names), with its printed total. | 2004 | 1 | 10 |

CSV files: `sources/data/report-dept-activity.csv`; `sources/data/report-library-service-values.csv`; `sources/data/report-town-facts.csv`; `sources/data/report-vehicle-inventory.csv`; `sources/data/report-weights-measures.csv`; `sources/data/report-series/building-activity.csv`; `sources/data/report-series/conservation-filings.csv`; `sources/data/report-series/cultural-council-grants.csv`; `sources/data/report-series/fire-calls.csv`; `sources/data/report-series/library-usage.csv`; `sources/data/report-series/nashoba-public-health.csv`; `sources/data/report-series/police-activity.csv`; `sources/data/report-series/town-facts.csv`; `sources/data/report-series/trade-permits.csv`.

### Other lists and one-offs

2 tables, 1,165 rows.

| Table | What it holds | Years | Editions | Rows |
|---|---|---|---:|---:|
| `series_small_one_offs` | Catch-all: small one-offs. Attendance Officer calls, trips, miles and contacts by month; the list of buildings the DPW maintains; retirees thanked at Annual Town… | 1959–FY2019 | 36 | 721 |
| `series_prose_boxed_as_tables` | Prose and lists boxed as tables. Paragraphs, lists and keys that the machine read as table cells: each list item is a row, each paragraph a row with its heading as the… | 1966–2010 | 17 | 444 |

CSV files: `sources/data/report-series/prose-boxed-as-tables.csv`; `sources/data/report-series/small-one-offs.csv`.

## Finding aids: tables about the reports themselves

These describe the documents rather than the town: what each page holds, which tables were catalogued, which pages were read and how.

| Table | What it holds | Rows |
|---|---|---:|
| `annual_report_catalogue` | A catalogue of what EXISTS, not of what has been extracted. | 3,676 |
| `series_coverage` | Which annual report editions were checked for each year-by-year series, and whether the series is printed there. | 3,082 |
| `annual_report_survey` | A measurement of PAGES, not of figures: per page, the extraction mode, how many gutters and money tokens it holds, how many characters and rows. | 2,751 |
| `series_report_contents_pages` | The report's own contents page. The department index at the front or back of each edition (none in 1986): one row per department or section, the first printed page as… | 2,637 |
| `report_index` | The town's OWN contents page of each annual report: every department and body it lists, the PRINTED page range of its report and the PDF pages that range lands on, or… | 702 |
| `report_anomalies` | Things found while reading the annual reports that need a person: a total that does not tie, a heading that moved, a column that vanished. | 521 |
| `series_scan_debris` | Scan debris and empty tables. Real captions, names and figures on pages where the machine read a table out of rules, photograph lettering or empty cells (covers,… | 208 |
| `annual_report_contents` | What was actually READ: which tables, from which pages, how many figures, and whether the extract is checkable against a printed total. | 199 |
| `report_filing` | Per body, which years it filed an annual report, which years the contents page printed `No Report Submitted`, and which years it was not listed at all. | 109 |

## What is not in the tables

- **174 pages are closed as unreadable or printed short**, each registered with its reason in `sources/data/page-blocked.csv`. Their words, where legible, are still in search.
- **Running prose is searchable but not tabulated.** Department narratives, by-law wording and letters are in the search index and the page text, not in table rows.
- **Some lists are one row per printed entry** (personnel changes, by-law articles), not split into columns.
- **"Not printed" in a series' coverage** rests partly on text searches rather than opened pages; each coverage row says which pages were looked at.

## The editions held

1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, FY 2011, FY 2012, FY 2013, FY 2014, FY 2015, FY 2016, FY 2016, Addendum, FY 2017, FY 2018, FY 2019, FY 2020, FY 2021, FY 2022, FY 2023, FY 2024, FY 2025.

