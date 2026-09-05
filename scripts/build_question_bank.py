#!/usr/bin/env python3
"""A hundred questions this archive can answer, each with the query that answers it.

    python3 scripts/build_question_bank.py [--check]

Writes `sources/analyses/questions.md` and `fy28/public/api/questions.json`.

WHY EVERY QUESTION CARRIES ITS SQL, AND WHY THEY ARE ALL RUN

A list of things a dataset "can answer" is a claim, and an unchecked claim about your own
data is the failure this project keeps meeting: a catalogue that named a document nobody
could download, an index whose shards resolved to nothing, a disclaimer that was two-thirds
false. So this is not a list of topics. Every entry is a query that is EXECUTED against the
database on every build, and the build fails if one errors or returns no rows.

That makes the document three things at once: a menu for a person, a set of worked examples
for an agent using `/api/query`, and a test that the tables still hold what this says they
hold. When a table is re-extracted and a column changes name, this breaks — which is the
point.

WHAT IT DELIBERATELY DOES NOT DO

It does not answer the questions. The numbers move when the data does, and a document
repeating them would go stale in exactly the way rule 2 warns about. It shows the shape of
the answer -- the columns and a couple of rows -- so a reader can see whether it is the
question they meant.

Several entries exist to demonstrate a rule rather than to be interesting: splitting on
`status` before aggregating an annual-report table, joining `dataset_document` to keep the
provenance, using `role_category` rather than the printed title. Those are the ones most
worth copying.
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT_MD = os.path.join(ROOT, 'sources', 'analyses', 'questions.md')
OUT_PLAIN = os.path.join(ROOT, 'sources', 'analyses', 'what-you-can-ask.md')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'api', 'questions.json')
SITE = 'https://lunenburgbudgetproject.org'

Q = []


def q(theme, question, sql, note=''):
    Q.append(dict(theme=theme, question=question, sql=' '.join(sql.split()), note=note))


# ---- the school budget ---------------------------------------------------------------
T = 'The school budget'
q(T, 'What did the district budget in total, in each year and at each stage?',
  "SELECT fy, stage, ROUND(SUM(value)) AS total FROM budget_figure GROUP BY fy, stage "
  "ORDER BY fy, stage",
  'A STAGE is not a period. `proposed`, `settled` and `actual` are three different '
  'documents about the same year, and mixing them is the error rule 1 exists for.')
q(T, 'Which budget lines grew fastest across the years the archive holds?',
  "WITH span AS (SELECT line_key, MIN(fy) AS first_fy, MAX(fy) AS last_fy "
  "FROM budget_figure WHERE stage='settled' GROUP BY line_key HAVING last_fy > first_fy) "
  "SELECT b.label, s.first_fy, s.last_fy, ROUND(a.value) AS started, "
  "ROUND(z.value) AS ended, ROUND(100.0*(z.value-a.value)/a.value,1) AS pct "
  "FROM span s JOIN budget_line b USING (line_key) "
  "JOIN budget_figure a ON a.line_key=s.line_key AND a.fy=s.first_fy AND a.stage='settled' "
  "JOIN budget_figure z ON z.line_key=s.line_key AND z.fy=s.last_fy AND z.stage='settled' "
  "WHERE a.value > 1000 ORDER BY pct DESC LIMIT 20",
  'Both ends are the SAME stage. A rate measured from an actual to a budget is partly '
  'growth and partly the step between them, which is rule 1.')
q(T, 'Which lines do two documents state differently, and by how much?',
  "SELECT label, fy, stage, ROUND(spread) AS spread FROM v_budget_disagreement "
  "WHERE spread > 0 ORDER BY spread DESC LIMIT 20",
  'The documents disagree with themselves by up to 1.5%, which is larger than most '
  'variances anybody wants to measure.')
q(T, 'What does each FY27 scenario total?',
  "SELECT variant, ROUND(SUM(value)) AS total, COUNT(*) AS lines FROM budget_figure "
  "WHERE fy=2027 AND variant IS NOT NULL GROUP BY variant ORDER BY total DESC")
q(T, 'How many budget lines are there in each section of the budget?',
  "SELECT section, COUNT(*) AS lines FROM budget_line GROUP BY section ORDER BY lines DESC")
q(T, 'Which function groups hold the most budget lines?',
  "SELECT function_group, COUNT(*) AS lines FROM budget_line WHERE function_group <> '' "
  "GROUP BY function_group ORDER BY lines DESC LIMIT 15")
q(T, 'What is in the FY27 workbook, by column?',
  "SELECT column_kind, COUNT(*) AS rows, ROUND(SUM(value)) AS total FROM workbook_figure "
  "WHERE row_kind='line' GROUP BY column_kind ORDER BY rows DESC",
  "Filter `row_kind='line'`: the sheet's own TOTAL rows are loaded too, and summing "
  'without the filter double-counts roughly fourfold.')
q(T, 'Which budget lines appear in the workbook but not in the line catalogue?',
  "SELECT DISTINCT w.line_key FROM workbook_figure w LEFT JOIN budget_line b "
  "USING (line_key) WHERE b.line_key IS NULL LIMIT 20")
q(T, 'How many figures rest on a document that two sources report differently?',
  "SELECT fy, COUNT(*) AS figures FROM budget_figure WHERE documents_disagree=1 "
  "GROUP BY fy ORDER BY fy")
q(T, 'What is the total salary line in each year, and does the stage change it?',
  "SELECT fy, stage, total FROM total_salaries_history ORDER BY fy, stage")
q(T, 'And total expenses?',
  "SELECT fy, stage, total FROM total_expenses_history ORDER BY fy, stage")

# ---- special education ----------------------------------------------------------------
T = 'Special education'
q(T, 'How many special education paraprofessionals were budgeted, by school and year?',
  "SELECT fy, stage, ps, es, ms, hs, total FROM sped_para_history ORDER BY fy, stage",
  'This is the line the 12.8% escalator rests on, and it is dollars, not people.')
q(T, 'And special education teachers?',
  "SELECT fy, stage, ps, es, ms, hs, total FROM sped_teacher_history ORDER BY fy, stage")
q(T, 'What has out-of-district tuition done, year by year?',
  "SELECT fy, stage, private, collaborative, total FROM ood_tuition_history ORDER BY fy, stage")
q(T, 'How many children were placed outside the district, and where?',
  "SELECT fy, as_of, total, collaborative, day, residential FROM placement_counts ORDER BY fy",
  'A count of children placed. It says nothing about which fund paid or what a placement '
  'cost, so it does not settle the money.')
q(T, 'Do the placement counts tie to their own parts, and to the prior year?',
  "SELECT fy, parts_tie, chain_agrees, report_says_prior_year FROM placement_counts ORDER BY fy")
q(T, 'What has special education transportation cost, by year?',
  "SELECT fy, stage, system, total FROM sped_transport_history ORDER BY fy, stage")
q(T, 'Does each year of the placement series agree with what the next report says of it?',
  "SELECT fy, total, report_says_prior_year, chain_agrees FROM placement_counts "
  "ORDER BY fy",
  'Two checks travel with this series: the parts sum to the total, and each year states '
  "the previous year's figure. `n/a` is the first year, which has nothing before it.")

# ---- the town's books ------------------------------------------------------------------
T = "The town's books"
q(T, 'What did each department spend against its budget, in the latest period held?',
  "SELECT a.dept, a.name, l.fy, l.period, ROUND(l.revised) AS revised, "
  "ROUND(l.expended) AS expended, ROUND(l.available) AS available FROM ledger_snapshot l "
  "JOIN account a USING (account_id) WHERE a.level='department' "
  "ORDER BY l.fy DESC, l.period DESC, l.revised DESC LIMIT 20")
q(T, 'Which departments are spending faster than the year is elapsing?',
  "SELECT dept, name, fy, period, ROUND(year_elapsed,2) AS year_elapsed, "
  "ROUND(spent_share,2) AS spent_share, ROUND(pace_gap,2) AS pace_gap FROM v_burn "
  "WHERE pace_gap IS NOT NULL ORDER BY pace_gap DESC LIMIT 20")
q(T, 'What funds does the town keep, and what restricts them?',
  "SELECT kind, COUNT(*) AS funds FROM fund GROUP BY kind ORDER BY funds DESC")
q(T, 'What moved through the special revenue funds in each year?',
  "SELECT fund, fy, period, ROUND(opening_balance) AS opening, ROUND(revenue) AS revenue, "
  "ROUND(expenditure) AS spent, ROUND(closing_balance) AS closing FROM fund_activity "
  "ORDER BY fy DESC, revenue DESC LIMIT 20")
q(T, 'How many accounts are there at each level of the chart?',
  "SELECT level, account_type, COUNT(*) AS accounts FROM account GROUP BY level, "
  "account_type ORDER BY accounts DESC")
q(T, 'Which grants did the district receive, and who owns them?',
  "SELECT fy, kind, name, ROUND(amount) AS amount, owner FROM grant_award "
  "ORDER BY fy DESC, amount DESC LIMIT 20")
q(T, 'What does the ledger hold for each fiscal year and period?',
  "SELECT fy, period, COUNT(*) AS rows, COUNT(DISTINCT account_id) AS accounts "
  "FROM ledger_snapshot GROUP BY fy, period ORDER BY fy, period",
  'Period 13 is the year-end close, after purchase orders are cleared. Period 12 is not '
  'the end of the year.')
q(T, 'Which function codes can be compared between the budget and the ledger?',
  "SELECT function_code, fy, period, ROUND(ledger_revised) AS revised, "
  "ROUND(ledger_expended) AS expended, budget_lines FROM v_function_budget_vs_ledger "
  "ORDER BY ledger_revised DESC LIMIT 20",
  'This is the level at which the two systems join. Below it they do not: the town '
  'shortens account names to ten characters.')
q(T, 'How much did each function group budget and spend across all years?',
  "SELECT function_group, years, ROUND(budgeted) AS budgeted, ROUND(spent) AS spent, "
  "ROUND(net) AS net, worst_year FROM variance_by_group ORDER BY ABS(net) DESC LIMIT 20")
q(T, 'What went through fund 1301, and when?',
  "SELECT fy, period, eff_date, src_meaning, COUNT(*) AS entries FROM fund_1301_cash_journal "
  "GROUP BY fy, period, eff_date, src_meaning ORDER BY fy DESC, eff_date DESC LIMIT 20")

# ---- staff -----------------------------------------------------------------------------
T = 'Staff on the rosters'
q(T, 'How many people of each kind did the town print on a roster, by year?',
  "SELECT fy, role_category, COUNT(*) AS people FROM v_staff_roster "
  "WHERE role_category <> 'unknown' GROUP BY fy, role_category ORDER BY fy, people DESC",
  'A count of names the town printed. It carries no FTE and no funding source, so it is '
  'not a staffing level.')
q(T, 'How many paraprofessionals, by school and year?',
  "SELECT fy, school, COUNT(*) AS paras FROM v_staff_roster "
  "WHERE role_category='paraprofessional' GROUP BY fy, school ORDER BY fy, paras DESC")
q(T, 'How many paraprofessionals were tied to a named grade?',
  "SELECT fy, role_grade, COUNT(*) AS paras FROM v_staff_roster "
  "WHERE role_category='paraprofessional' AND role_grade <> '' "
  "GROUP BY fy, role_grade ORDER BY fy, role_grade")
q(T, 'What did the town print as the title for a paraprofessional, year by year?',
  "SELECT fy, role_raw, COUNT(*) AS rows FROM v_staff_roster "
  "WHERE role_category='paraprofessional' AND role_raw <> '' "
  "GROUP BY fy, role_raw ORDER BY fy, rows DESC",
  'Tutor, Aide, Tutors/Aides, Paraprofessional, Para, (para), Sped Para. Five names for '
  'one job across fifteen years, which is why `role_category` exists.')
q(T, 'Which roster titles could not be classified at all?',
  "SELECT role_raw, grade_or_dept, rows FROM role_classification "
  "WHERE role_category='unknown' ORDER BY rows DESC LIMIT 20",
  'Left `unknown` rather than guessed. 8% of rows.')
q(T, 'Which rule decided each classification, and how much rests on the weakest ones?',
  "SELECT classified_by, role_category, SUM(rows) AS rows FROM role_classification "
  "GROUP BY classified_by, role_category ORDER BY rows DESC",
  'A rule beginning `heading-` read the section heading rather than a printed title, '
  'which is weaker evidence.')
q(T, 'How many names appear on each school roster in each year?',
  "SELECT fy, school, position, count FROM staff_roster_counts ORDER BY fy DESC, count DESC LIMIT 20")
q(T, 'How many teachers were printed against a specific grade?',
  "SELECT fy, role_grade, COUNT(*) AS teachers FROM v_staff_roster "
  "WHERE role_category='teacher' AND role_grade <> '' GROUP BY fy, role_grade "
  "ORDER BY fy DESC, role_grade")
q(T, 'Which schools have roster entries, and for which years?',
  "SELECT school, COUNT(DISTINCT fy) AS years, MIN(fy) AS first, MAX(fy) AS last, "
  "COUNT(*) AS rows FROM staff_roster_entries GROUP BY school ORDER BY rows DESC")
q(T, 'How many counselors, nurses, psychologists and social workers, by year?',
  "SELECT fy, role_category, COUNT(*) AS people FROM v_staff_roster WHERE role_category "
  "IN ('counselor','nurse','psychologist','social_worker','speech_therapist') "
  "GROUP BY fy, role_category ORDER BY fy, role_category")

# ---- athletics and fees -----------------------------------------------------------------
T = 'Athletics and fees'
q(T, 'What did each sport cost, and how many played?',
  "SELECT fy, season, level, sport, metric, value FROM athletics_by_sport "
  "WHERE is_numeric='1' ORDER BY fy DESC, value DESC LIMIT 20")
q(T, 'Do the per-sport figures add up to the totals the district printed?',
  "SELECT season, scope, metric, fy, printed, summed_from_rows, difference, ties "
  "FROM athletics_by_sport_reconciliation ORDER BY ABS(CAST(difference AS REAL)) DESC LIMIT 20")
q(T, 'What has athletics cost and raised, year by year?',
  "SELECT fy, side, item, amount, basis FROM athletics_history ORDER BY fy DESC, side")
q(T, 'What has the athletic fee been, by year and tier?',
  "SELECT fy, school_year, level, item, amount, unit, verified FROM athletic_fee_schedule "
  "ORDER BY fy DESC, level")
q(T, 'Which rates does this project know about, and which does it use?',
  "SELECT fy, category, item, value, value_type, set_on FROM rate_register "
  "ORDER BY fy DESC, category LIMIT 20",
  'It deliberately includes rates the model does NOT use, and the ones that cannot be '
  'stated at all.')
q(T, 'Which rates were set by a document we hold, and which were not?',
  "SELECT category, COUNT(*) AS rates, SUM(CASE WHEN source_file <> '' THEN 1 ELSE 0 END) "
  "AS with_a_document FROM rate_register GROUP BY category ORDER BY rates DESC")

# ---- the annual town reports --------------------------------------------------------------
T = 'The annual town reports'
q(T, 'What appropriations did each annual report print, and are the rows checked?',
  "SELECT edition, status, COUNT(*) AS rows FROM report_appropriations "
  "GROUP BY edition, status ORDER BY edition, rows DESC",
  'ALWAYS split on `status`. `checked`, `check failed` and `no check` are three different '
  'claims and nothing may be aggregated across them.')
q(T, 'What did the town pay in gross wages, and to how many people?',
  "SELECT edition, status, COUNT(*) AS rows FROM report_gross_wages "
  "GROUP BY edition, status ORDER BY edition")
q(T, 'What debt has the town carried?',
  "SELECT edition, COUNT(*) AS rows, SUM(CASE WHEN status='checked' THEN 1 ELSE 0 END) "
  "AS checked FROM report_debt GROUP BY edition ORDER BY edition")
q(T, 'What capital projects did the reports list?',
  "SELECT edition, label, status FROM report_capital_projects "
  "WHERE label <> '' ORDER BY edition DESC LIMIT 20")
q(T, 'What is in the trust funds?',
  "SELECT edition, COUNT(*) AS rows FROM report_trust_funds GROUP BY edition ORDER BY edition")
q(T, 'What did the town value its property at?',
  "SELECT edition, label, status FROM report_valuation WHERE label <> '' "
  "ORDER BY edition DESC LIMIT 20")
q(T, 'What enrollment and MCAS results were printed?',
  "SELECT edition, COUNT(*) AS rows FROM report_enrollment_mcas GROUP BY edition ORDER BY edition")
q(T, 'What did the town assess for Monty Tech?',
  "SELECT edition, label, status FROM report_monty_tech WHERE label <> '' ORDER BY edition DESC LIMIT 20")
q(T, 'How many births, deaths and marriages were recorded?',
  "SELECT edition, label, status FROM report_vital_records WHERE label <> '' ORDER BY edition DESC LIMIT 20")
q(T, 'Who held town office, and when?',
  "SELECT edition, label FROM report_officials WHERE label <> '' ORDER BY edition DESC LIMIT 20")
q(T, 'What did each department report doing?',
  "SELECT edition, COUNT(*) AS rows FROM report_dept_activity GROUP BY edition ORDER BY edition")
q(T, 'What receipts did the town record, and from what source?',
  "SELECT fy, source, amount, status FROM annual_report_receipts ORDER BY fy DESC, "
  "CAST(amount AS REAL) DESC LIMIT 20")
q(T, 'What tables does each annual report contain?',
  "SELECT fy, [table], pages, figure_rows, checkable FROM annual_report_contents "
  "ORDER BY fy DESC, figure_rows DESC LIMIT 20")
q(T, 'Which tables in the reports were read, and which are still uncaptured?',
  "SELECT dataset, COUNT(*) AS editions, SUM(CASE WHEN extractable='yes' THEN 1 ELSE 0 END) "
  "AS extractable FROM extraction_plan GROUP BY dataset ORDER BY editions DESC LIMIT 20")
q(T, 'What did the survey find on each page of each report?',
  "SELECT fy, mode, COUNT(*) AS pages, SUM(money) AS money_tokens FROM annual_report_survey "
  "GROUP BY fy, mode ORDER BY fy, pages DESC")
q(T, 'What is catalogued in each report, by printed heading?',
  "SELECT fy, printed_heading, pages, grain FROM annual_report_catalogue "
  "WHERE printed_heading <> '' ORDER BY fy DESC LIMIT 20")
q(T, 'Where did the extraction find something it could not reconcile?',
  "SELECT fy, edition, [table], kind, detail FROM report_anomalies ORDER BY fy DESC LIMIT 20",
  'An anomaly is a finding about our reading of the page as much as about the page.')
q(T, 'Which special revenue funds appear in the reports, and in which years?',
  "SELECT fy, [group], COUNT(*) AS rows FROM special_revenue_funds GROUP BY fy, [group] "
  "ORDER BY fy DESC, rows DESC LIMIT 20")

# ---- money coming in ---------------------------------------------------------------------
T = 'Revenue, tax base and free cash'
q(T, 'What free cash has each town certified, and from what?',
  "SELECT town, year, line, amount, role FROM free_cash_proof ORDER BY year DESC, town LIMIT 20",
  'Absolute dollars with no denominator, so they do not compare between towns of '
  'different size. The composition does compare, because a share has no size.')
q(T, 'How does Lunenburg free cash compare with its neighbours, by composition?',
  "SELECT town, year, line, amount FROM free_cash_proof WHERE role='component' "
  "ORDER BY year DESC, town LIMIT 20")
q(T, 'What has the town spent on capital, and where did the money come from?',
  "SELECT fy, total, free_cash, taxation, unexpended_prior_year_capital, other "
  "FROM capital_funding_history ORDER BY fy")
q(T, 'What is in the FY27 capital plan, and what is funded?',
  "SELECT rank, dept, project, cost, funded, funding FROM capital_plan_fy27 ORDER BY rank")
q(T, 'How do state measures compare Lunenburg with other districts?',
  "SELECT district, fy, measure, value FROM dese_measure WHERE district <> '' "
  "ORDER BY fy DESC LIMIT 20")
q(T, 'Which DESE measures reconcile against the printed totals, and which do not?',
  "SELECT measure, COUNT(*) AS rows, SUM(CASE WHEN reconciles='1' THEN 1 ELSE 0 END) "
  "AS reconciling FROM dese_measure GROUP BY measure ORDER BY rows DESC LIMIT 15")

# ---- votes ---------------------------------------------------------------------------------
T = 'Votes and elections'
q(T, 'What has the town been asked to fund, and did it agree?',
  "SELECT date, election, question, type, amount, yes, no, total FROM ballot_questions "
  "ORDER BY date DESC")
q(T, 'What turnout did each ballot question draw?',
  "SELECT date, question, total, registered, ROUND(100.0*total/registered,1) AS turnout_pct "
  "FROM ballot_questions WHERE registered > 0 ORDER BY date DESC")
q(T, 'What election results did the annual reports print?',
  "SELECT edition, COUNT(*) AS rows FROM report_elections GROUP BY edition ORDER BY edition")

# ---- provenance and data quality ---------------------------------------------------------
T = 'Provenance, and what is not established'
q(T, 'Where did a figure in this dataset come from?',
  "SELECT dataset, edition, document, publisher_label, sha256 FROM dataset_document "
  "ORDER BY dataset, edition LIMIT 20",
  'This is the join that gives an annual-report row an address. Use it in any query whose '
  'answer somebody might want to check.')
q(T, 'Which documents does the archive hold, and how were they obtained?',
  "SELECT source_type, basis, COUNT(*) AS documents FROM document "
  "GROUP BY source_type, basis ORDER BY documents DESC")
q(T, 'Which documents no longer open at the publisher, or no longer match our copy?',
  "SELECT doc_id, link_state, copy_state, url FROM document "
  "WHERE copy_state NOT IN ('identical','') OR link_state NOT IN ('200','') LIMIT 20")
q(T, 'Which documents have no upstream address at all?',
  "SELECT doc_id, source_type FROM document WHERE url IS NULL OR url='' LIMIT 20",
  "A gap on our side, not the town's: they were gathered before the mirror existed "
  'and '
  'nobody wrote down where they came from.')
q(T, 'Where do two sources state the same budget line differently?',
  "SELECT label, fy, stage, source, value, is_kept FROM line_history_disagreements "
  "ORDER BY fy DESC, label LIMIT 20")
q(T, 'How much of each dataset has been checked against the page it came from?',
  "SELECT dataset, reconciled, partial, SUM(CAST(rows AS INTEGER)) AS rows "
  "FROM dataset_document GROUP BY dataset, reconciled, partial ORDER BY rows DESC LIMIT 20")
q(T, 'Which figures has somebody stated publicly, and on what basis?',
  "SELECT fy, metric, amount, stated_by, stated_on, basis FROM stated_figure ORDER BY fy DESC")
q(T, 'Which budget lines have no ledger account mapped to them?',
  "SELECT COUNT(*) AS budget_lines, (SELECT COUNT(*) FROM crosswalk) AS mapped "
  "FROM budget_line",
  'The crosswalk is empty ON PURPOSE. District lines are named, MUNIS rows are coded, and '
  'no published document maps one to the other. Budget-to-actual at line level cannot be '
  'answered from this data.')
q(T, 'Which pages of the annual reports have columns we could not establish?',
  "SELECT edition, COUNT(*) AS rows FROM report_appropriations "
  "WHERE column_meaning LIKE 'not established%' GROUP BY edition ORDER BY rows DESC",
  '`v1` is an ordinal -- the first column of THIS page that held figures -- not a column '
  'name. Read `column_meaning` before summing anything.')
q(T, 'How many rows of each report table failed their own check?',
  "SELECT 'appropriations' AS t, status, COUNT(*) AS rows FROM report_appropriations "
  "GROUP BY status UNION ALL SELECT 'gross_wages', status, COUNT(*) FROM report_gross_wages "
  "GROUP BY status ORDER BY t, rows DESC")

# ---- getting started ------------------------------------------------------------------------
T = 'Finding your way'
q(T, 'What tables are there, and how big are they?',
  "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name")
q(T, 'What fiscal years does the archive cover, per dataset?',
  "SELECT dataset, MIN(edition) AS first, MAX(edition) AS last, COUNT(*) AS editions "
  "FROM dataset_document GROUP BY dataset ORDER BY dataset")
q(T, 'What does one fiscal period mean?',
  "SELECT period, label, months_elapsed, is_final FROM fiscal_period ORDER BY period")


# ---- added to round out the hundred -------------------------------------------------------
T = 'The school budget'
q(T, 'What is the biggest single line in the budget, in each year?',
  "SELECT f.fy, b.label, ROUND(MAX(f.value)) AS value FROM budget_figure f "
  "JOIN budget_line b USING (line_key) WHERE f.stage='settled' GROUP BY f.fy "
  "ORDER BY f.fy DESC")
q(T, 'How many lines does each budget document state?',
  "SELECT doc_id, COUNT(*) AS figures, COUNT(DISTINCT fy) AS years FROM budget_figure "
  "GROUP BY doc_id ORDER BY figures DESC LIMIT 15")
q(T, 'Which lines exist in one scenario but not another?',
  "SELECT line_key, COUNT(DISTINCT variant) AS variants FROM budget_figure "
  "WHERE fy=2027 AND variant IS NOT NULL GROUP BY line_key ORDER BY variants LIMIT 15")
q(T, 'What does the FY27 workbook say each line was in FY25?',
  "SELECT line_key, column_kind, ROUND(value) AS value FROM workbook_figure "
  "WHERE fy=2025 AND row_kind='line' ORDER BY value DESC LIMIT 20")

T = "The town's books"
q(T, 'Which accounts had the largest unspent balance at the latest period?',
  "SELECT a.name, a.fund_name, l.fy, l.period, ROUND(l.available) AS available "
  "FROM ledger_snapshot l JOIN account a USING (account_id) "
  "ORDER BY l.fy DESC, l.period DESC, l.available DESC LIMIT 20")
q(T, 'How much was transferred into or out of each account?',
  "SELECT a.name, l.fy, l.period, ROUND(l.transfers) AS transfers FROM ledger_snapshot l "
  "JOIN account a USING (account_id) WHERE l.transfers <> 0 "
  "ORDER BY ABS(l.transfers) DESC LIMIT 20",
  '`transfers` is CUMULATIVE. Movement between two periods is the difference of the '
  'column, never the later value.')
q(T, 'Which accounts are revenue rather than expenditure?',
  "SELECT account_type, level, COUNT(*) AS accounts FROM account "
  "GROUP BY account_type, level ORDER BY accounts DESC",
  'Revenue rows are stored NEGATIVE, exactly as MUNIS prints them. Check '
  '`account_type` before doing arithmetic across types.')
q(T, 'What share of its budget had each department used?',
  "SELECT a.dept, a.name, l.fy, l.period, ROUND(l.pct_used,1) AS pct_used "
  "FROM ledger_snapshot l JOIN account a USING (account_id) WHERE l.pct_used IS NOT NULL "
  "ORDER BY l.pct_used DESC LIMIT 20")

T = 'Staff on the rosters'
q(T, 'How many people did the town print on a roster in total, by year?',
  "SELECT fy, COUNT(*) AS names, COUNT(DISTINCT school) AS schools FROM v_staff_roster "
  "GROUP BY fy ORDER BY fy")
q(T, 'Which names appear across the most years?',
  "SELECT name, COUNT(DISTINCT fy) AS years, MIN(fy) AS first, MAX(fy) AS last "
  "FROM staff_roster_entries WHERE name <> '' GROUP BY name "
  "ORDER BY years DESC, name LIMIT 20",
  'A name printed in a public annual report. It is not a claim about employment, and a '
  'roster gives no FTE.')
q(T, 'How many administrators did each school print?',
  "SELECT fy, school, COUNT(*) AS admins FROM v_staff_roster "
  "WHERE role_category='administrator' GROUP BY fy, school ORDER BY fy DESC, admins DESC "
  "LIMIT 20")
q(T, 'Which grades appear anywhere on the rosters?',
  "SELECT role_grade, COUNT(*) AS rows FROM v_staff_roster WHERE role_grade <> '' "
  "GROUP BY role_grade ORDER BY rows DESC")

T = 'The annual town reports'
q(T, 'How many figures did each annual report yield, and how many were checked?',
  "SELECT edition, COUNT(*) AS rows, "
  "SUM(CASE WHEN status='checked' THEN 1 ELSE 0 END) AS checked FROM report_appropriations "
  "GROUP BY edition ORDER BY edition")
q(T, 'Which report tables print a total we can reconcile to?',
  "SELECT fy, [table], printed_total, checkable FROM annual_report_contents "
  "WHERE printed_total <> '' ORDER BY fy DESC LIMIT 20")
q(T, 'How many pages of each report carried figures at all?',
  "SELECT fy, COUNT(*) AS pages, SUM(CASE WHEN money > 0 THEN 1 ELSE 0 END) AS with_money "
  "FROM annual_report_survey GROUP BY fy ORDER BY fy")
q(T, 'What kinds of anomaly did the extraction find, and how often?',
  "SELECT kind, COUNT(*) AS occurrences FROM report_anomalies GROUP BY kind "
  "ORDER BY occurrences DESC")

T = 'Revenue, tax base and free cash'
q(T, 'How has free cash moved for Lunenburg specifically?',
  "SELECT year, line, amount, role FROM free_cash_proof WHERE town='Lunenburg' "
  "ORDER BY year DESC, line")
q(T, 'Which towns does the free cash comparison cover?',
  "SELECT town, COUNT(DISTINCT year) AS years, MIN(year) AS first, MAX(year) AS last "
  "FROM free_cash_proof GROUP BY town ORDER BY town")
q(T, 'What measures does the state publish about this district?',
  "SELECT measure, COUNT(*) AS rows, MIN(fy) AS first, MAX(fy) AS last FROM dese_measure "
  "GROUP BY measure ORDER BY rows DESC LIMIT 15")

T = 'Provenance, and what is not established'
q(T, 'Which documents were obtained by records request rather than published?',
  "SELECT source_type, COUNT(*) AS documents FROM document GROUP BY source_type "
  "ORDER BY documents DESC")
q(T, 'What basis does each document have for the figures it prints?',
  "SELECT basis, COUNT(*) AS documents FROM document WHERE basis IS NOT NULL "
  "GROUP BY basis ORDER BY documents DESC",
  '`ledger` means a figure exists because a transaction did. `restatement` means a prior '
  'year re-presented by the party that spent it. They are not interchangeable.')
q(T, 'Which datasets have a document for every edition, and which do not?',
  "SELECT dataset, COUNT(*) AS editions, SUM(CASE WHEN document <> '' THEN 1 ELSE 0 END) "
  "AS with_a_document FROM dataset_document GROUP BY dataset ORDER BY editions DESC")
q(T, 'How many rows of each dataset came off each page?',
  "SELECT dataset, edition, pages, rows FROM dataset_document "
  "ORDER BY CAST(rows AS INTEGER) DESC LIMIT 20")


def run(db):
    """Every query, executed. A question that does not answer is not a question."""
    results, failed = [], []
    for item in Q:
        try:
            cur = db.execute(item['sql'])
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(3)
        except Exception as e:                                   # noqa: BLE001
            failed.append((item['question'], str(e)))
            continue
        if not rows:
            failed.append((item['question'], 'returned no rows'))
            continue
        results.append(dict(item, columns=cols,
                            sample=[dict(zip(cols, r)) for r in rows]))
    return results, failed


def render(results):
    by = {}
    for r in results:
        by.setdefault(r['theme'], []).append(r)
    L = ['# A hundred questions this archive can answer', '',
         '**Generated by `scripts/build_question_bank.py`. Do not edit.**', '',
         f'Every query below is run against the database on each build, and the build '
         f'fails if one errors or returns nothing. {len(results)} questions across '
         f'{len(by)} subjects.', '',
         'Run any of them yourself:', '',
         '```',
         f'curl -s -X POST {SITE}/api/query \\',
         "  -H 'content-type: application/json' \\",
         '  -d \'{"sql": "SELECT fy, COUNT(*) FROM v_staff_roster '
         "WHERE role_category = ''paraprofessional'' GROUP BY fy\"}'",
         '```', '',
         f'Or download the database: `{SITE}/data/lunenburg.db`. '
         f'Read `{SITE}/api/schema` first — it states the grain of every table and the '
         f'specific ways to get a confident wrong answer out of this data.', '',
         '**These are not answers.** The numbers move when the data does, so this shows '
         'the shape of each result — its columns and a row or two — rather than repeating '
         'figures that would go stale. Several entries exist to demonstrate a rule rather '
         'than to be interesting; those carry a note and are the ones worth copying.', '']
    for theme in by:
        L += [f'## {theme}', '']
        for r in by[theme]:
            L.append(f'**{r["question"]}**')
            L.append('')
            L.append('```sql')
            L.append(r['sql'])
            L.append('```')
            L.append('')
            L.append(f'Returns `{"`, `".join(r["columns"])}` — for example: '
                     + '; '.join(', '.join(f'{k}={v}' for k, v in s.items())
                                 for s in r['sample'][:1]))
            L.append('')
            if r['note']:
                L.append(f'> {r["note"]}')
                L.append('')
    return '\n'.join(L) + '\n'


# The notes are written once, for both documents, and they carry the project's own
# shorthand: backticked column names, and references to the numbered rules in CLAUDE.md.
# Neither means anything to a resident. These substitutions are listed rather than done
# with a clever regex so that anybody can see exactly what the plain version says
# differently -- the two files must not come to mean different things.
PLAIN = [
    (', and mixing them is the error rule 1 exists for', ', and they must never be mixed'),
    (', which is rule 1', ''),
    (' which is rule 1', ''),
    ('rule 12', 'the rule that every figure must be traceable to a document'),
    ('rule 2', 'the rule that no figure is ever typed into a sentence'),
    ('rule 7', 'the rule that separates a measurement from an explanation for it'),
]


def humanise(note):
    for a, b in PLAIN:
        note = note.replace(a, b)
    return note.replace('`', '')


def render_plain(results):
    """The same questions, for somebody who is not going to write a query.

    Generated from the same list as `questions.md`, so the two cannot drift into offering
    different things -- which is the only reason it is worth having two.

    The notes are kept and the SQL is dropped. That is deliberate: the note is the half a
    resident most needs, because it says what a figure does NOT tell you. "How many
    paraprofessionals" without "this is a count of names the town printed, with no FTE and
    no funding source" is the kind of number that gets quoted at a meeting and cannot be
    defended.
    """
    by = {}
    for r in results:
        by.setdefault(r['theme'], []).append(r)
    L = ['# What you can ask this archive', '',
         '**Generated by `scripts/build_question_bank.py`. Do not edit.**', '',
         f'{len(results)} questions this archive can answer, in plain English. Every one '
         f'has been run against the data, so nothing on this list is a question we merely '
         f'hope is answerable.', '',
         'Some carry a second line in italics. That line says what the answer does **not** '
         'tell you, and it is usually the more important half: a figure quoted without it '
         'is the kind that cannot be defended when somebody asks where it came from.', '',
         'The same list with the query behind each question is at '
         f'[questions.md]({SITE}/docs/analyses/questions.md), and anyone can run those '
         f'against the data at [{SITE}/api/query]({SITE}/api/query).', '',
         '---', '']
    for theme in by:
        L += [f'## {theme}', '']
        for r in by[theme]:
            L.append(f'- {r["question"]}')
            if r['note']:
                L.append(f'  *{humanise(r["note"])}*')
        L.append('')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if not os.path.exists(DB):
        sys.exit('no database; run scripts/build_db.py first')
    db = sqlite3.connect(DB)
    results, failed = run(db)

    if failed:
        print(f'{len(failed)} of {len(Q)} questions do not answer:')
        for question, why in failed:
            print(f'  {question}\n      {why}')
        print('\n  A question bank whose questions do not run is a list of claims about '
              'the data.\n  Fix the query or drop the question.')
        return 1

    body = render(results)
    payload = dict(
        resource='questions',
        about='Questions this archive can answer, each with the SQL that answers it. '
              'Every one is executed on each build; the build fails if one stops '
              'answering.',
        endpoint=f'{SITE}/api/query',
        readFirst=f'{SITE}/api/schema',
        count=len(results),
        questions=[{k: r[k] for k in ('theme', 'question', 'sql', 'note', 'columns')}
                   for r in results],
    )
    text = json.dumps(payload, indent=1) + '\n'

    plain = render_plain(results)

    if args.check:
        stale = [p for p, want in ((OUT_MD, body), (OUT_PLAIN, plain), (OUT_JSON, text))
                 if not os.path.exists(p) or open(p).read() != want]
        if stale:
            print('STALE  ' + ', '.join(os.path.relpath(p, ROOT) for p in stale)
                  + '\n  Run: python3 scripts/build_question_bank.py')
            return 1
        print(f'ok: {len(results)} questions, all answering')
        return 0

    open(OUT_MD, 'w').write(body)
    open(OUT_PLAIN, 'w').write(plain)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    open(OUT_JSON, 'w').write(text)
    print(f'{len(results)} questions across {len(set(r["theme"] for r in results))} '
          f'subjects, all answering')
    print(f'  wrote {os.path.relpath(OUT_MD, ROOT)}')
    print(f'  wrote {os.path.relpath(OUT_PLAIN, ROOT)}')
    print(f'  wrote {os.path.relpath(OUT_JSON, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
