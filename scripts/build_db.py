"""Build the analysis database from the extracted CSVs.

The CSVs in `sources/data/` are the source of truth and stay that way. This file is a
**derived read model**: it is dropped and rebuilt from scratch on every run, it is never
written to by hand, and deleting it loses nothing. That distinction is load-bearing --
a row in a database has no address, no publisher filename and no sha256, so the moment a
figure is edited here rather than extracted into here, rules 12 and 13 are broken.

    python3 scripts/build_db.py            # rebuild sources/data/lunenburg.db
    python3 scripts/build_db.py --check    # rebuild, then assert the reconciliations

Only the standard library. `sqlite3` ships with Python and the `sqlite3` binary ships with
macOS, so a resident can open the result without installing anything.

---------------------------------------------------------------------------------------
THE GRAIN, which is the part that matters
---------------------------------------------------------------------------------------

Two fact tables, two different grains, one shared dimension.

  ledger_snapshot   one row per (fund, account, fiscal year, PERIOD, document)
                    Measures: original, transfers, revised, expended, encumbered,
                    available. This is a PERIODIC SNAPSHOT -- the same account reappears
                    at period 3, 6, 9, 13 -- and it is the periodicity that makes
                    intra-year transfer tracking and burn-rate analysis possible at all.
                    Period 13 is the year-end close, after the lapse period.

  budget_figure     one row per (line, fiscal year, STAGE, VARIANT, document)
                    Stage is what the figure IS: proposed / settled / restated. A stage is
                    never a period and the two must not be joined as though they were.

  account           the CONFORMED DIMENSION. Both facts point at it. Until the line-level
                    MUNIS reports arrive, the only accounts we hold are department
                    rollups, so `account.level` says which we have.

  crosswalk         line <-> account, and it is EXPECTED TO BE INCOMPLETE. Every row
                    carries how the mapping was established and what evidence supports
                    it. An empty crosswalk is the honest state today; a crosswalk full of
                    guesses would be rule 13's exact failure.

Every fact row carries `doc_id`, so the address travels with the number into the database
and back out of any query. A figure that cannot name its document does not get loaded.
"""
import argparse
import csv
import glob
import hashlib
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
DB = os.path.join(DATA, 'lunenburg.db')

SCHEMA = """
-- ------------------------------------------------------------------ dimensions

-- Provenance, carried into the database rather than left behind in the archive.
-- `basis` is what produced the figures: ledger / restatement / forward / narrative.
CREATE TABLE document (
    doc_id              TEXT PRIMARY KEY,   -- the archive path, or the CSV stem
    path                TEXT,
    source_type         TEXT,
    basis               TEXT,
    ledger_at           TEXT,               -- where the ledger column is, if any
    hidden_columns      TEXT,               -- what a reader does NOT see (rule 13)
    url                 TEXT,
    link_state          TEXT,               -- from link-status.csv
    copy_state          TEXT,               -- identical / repackaged / differs / ...
    remote_sha256       TEXT,
    local_sha256        TEXT
);

-- Funds. The general fund is one of many, and rule 11 is entirely about the others:
-- a general fund line is NET of whatever a grant, fee or revolving fund already paid.
CREATE TABLE fund (
    fund                TEXT PRIMARY KEY,   -- '0100', '1301', '2200', '6100'
    name                TEXT,
    kind                TEXT,               -- general | enterprise | revolving | grant | gift
    restriction         TEXT                -- what the money may be spent on, if stated
);

-- The conformed dimension. One row per account as the ledger knows it.
-- `level` distinguishes what we actually hold: 'department' is a rollup, 'account' is
-- the line-level detail that arrives only with Print totals only: N.
CREATE TABLE account (
    account_id          TEXT PRIMARY KEY,   -- e.g. '0100-300' or '0100-300-5110'
    fund                TEXT NOT NULL,      -- '0100' general fund, grant/revolving funds
    fund_name           TEXT,
    dept                TEXT,               -- '300' SCHOOL DEPARTMENT
    org                 TEXT,
    object              TEXT,
    -- The account string as MUNIS prints it in a SPREADSHEET export, and the function
    -- code carried in its fourth segment. Both were being discarded by the loader.
    --
    -- This is the join to the district's budget, and it was sitting in munis-ledger.csv
    -- the whole time. `function` matches `budget_line.function_group` on its first four
    -- characters for 41 of the budget's 45 codes. Without these two columns `crosswalk`
    -- could not be populated by anything, the API could not express the join, and an
    -- analysis run against this database concluded the two sides shared no key at all.
    --
    -- NULL for every row that came from a PDF: the printed report shows ORG and OBJ and
    -- not the account string, which is why `function` is populated for FY2026 period 12
    -- and nothing earlier. A null here means the report was a PDF, not that the account
    -- has no function.
    account_string      TEXT,
    function            TEXT,
    name                TEXT,
    account_type        TEXT NOT NULL       -- 'expense' | 'revenue'
        CHECK (account_type IN ('expense', 'revenue')),
    level               TEXT NOT NULL       -- 'department' | 'account'
        CHECK (level IN ('department', 'account')),
    first_seen_fy       INTEGER,
    last_seen_fy        INTEGER
);

-- Budget lines as the district's own documents name them. No account code: they do not
-- print one. That is the whole reason `crosswalk` exists.
CREATE TABLE budget_line (
    line_key            TEXT PRIMARY KEY,   -- normalised name
    label               TEXT,               -- as printed
    section             TEXT,               -- EXPENSES / SALARIES
    function_group      TEXT,               -- '1110 - School Committee'
    kind                TEXT
);

-- Deliberately incomplete. `method` records HOW a mapping was established; `evidence`
-- quotes what supports it. Nothing is inserted here by inference from a similar name.
CREATE TABLE crosswalk (
    line_key            TEXT NOT NULL REFERENCES budget_line(line_key),
    account_id          TEXT NOT NULL REFERENCES account(account_id),
    method              TEXT NOT NULL,      -- 'published' | 'reconciled' | 'stated'
    confidence          TEXT NOT NULL,      -- 'certain' | 'probable' | 'candidate'
    evidence            TEXT NOT NULL,      -- a coordinate and a raw value
    doc_id              TEXT REFERENCES document(doc_id),
    PRIMARY KEY (line_key, account_id)
);

-- Named periods, so a query never has to hard-code that 13 means the year-end close.
CREATE TABLE fiscal_period (
    period              INTEGER PRIMARY KEY,
    label               TEXT NOT NULL,
    months_elapsed      REAL,               -- through the end of that period
    is_final            INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------------ facts

-- PERIODIC SNAPSHOT. One row per account per period per document.
-- available = revised - expended - encumbered, and the surplus at period 13 IS available.
CREATE TABLE ledger_snapshot (
    account_id          TEXT NOT NULL REFERENCES account(account_id),
    fy                  INTEGER NOT NULL,
    period              INTEGER NOT NULL REFERENCES fiscal_period(period),
    original            REAL,               -- as appropriated
    transfers           REAL,               -- transfers / adjustments since
    revised             REAL,               -- original + transfers
    expended            REAL,
    encumbered          REAL,
    available           REAL,
    pct_used            REAL,               -- as the report prints it
    rounded_columns     TEXT,               -- which measures the source rounded
    doc_id              TEXT NOT NULL REFERENCES document(doc_id),
    PRIMARY KEY (account_id, fy, period, doc_id)
);

-- One row per budget line per year per STAGE. From line-history.csv, which is already
-- tidy: 19,453 readings normalised to distinct lines across 24 documents.
CREATE TABLE budget_figure (
    line_key            TEXT NOT NULL,
    label               TEXT,
    fy                  INTEGER NOT NULL,
    -- 'proposed'  what the district asked for
    -- 'settled'   what was voted
    -- 'restated'  what the district later re-presented as spent, INSIDE ITS OWN BUDGET
    --             BOOK. NOT a ledger figure. Renamed from 'actual' on 7 September 2026
    --             because the old name was read as the accounting system and produced a
    --             written claim that twelve years of school actuals were available. They
    --             are not: the ledger reaches school spending for FY2026 period 12 and one
    --             quarter of FY23. See check_no_stage_actual() below.
    stage               TEXT NOT NULL
        CHECK (stage IN ('proposed', 'settled', 'restated')),
    -- The document's own name for the column, where it named one: 'Balanced',
    -- 'Core Budget', 'Level Service', 'Restoration'. Empty for a document that prints
    -- one column per stage, which is most of them.
    --
    -- A SCENARIO IS NOT A DISAGREEMENT. The FY27 budget document prints four FY27
    -- columns; they are four proposals, not four opinions about one figure, and folding
    -- them onto one key would keep whichever was read last. Every query that wants "the"
    -- budget for a year must say `variant = ''` or it will count a line four times --
    -- the same rule as workbook_figure's row_kind='line'.
    variant             TEXT NOT NULL DEFAULT '',
    value               REAL NOT NULL,
    documents_disagree  INTEGER NOT NULL DEFAULT 0,
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (line_key, fy, stage, variant, doc_id)
);

-- The FY27 workbook, wide columns unpivoted to one row per (line, fy, column).
-- Column kinds are the workbook's own headers, not our interpretation of them.
CREATE TABLE workbook_figure (
    row                 INTEGER NOT NULL,   -- the worksheet row, so a cell is quotable
    line_key            TEXT NOT NULL,
    fy                  INTEGER NOT NULL,
    column_kind         TEXT NOT NULL,      -- 'actual' | 'budget' | 'final_budget' | ...
    value               REAL NOT NULL,
    row_kind            TEXT NOT NULL       -- 'line' | 'total'
        CHECK (row_kind IN ('line', 'total')),
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (row, fy, column_kind, doc_id)
);

-- Fund balance activity: what a fund took in, spent, and carried. This is the shape the
-- district's own fund workbooks publish, and it is NOT the ledger's shape -- a fund has a
-- balance that rolls forward, a department has an appropriation that lapses.
CREATE TABLE fund_activity (
    fund                TEXT NOT NULL,
    fy                  INTEGER NOT NULL,
    period              INTEGER,
    opening_balance     REAL,
    revenue             REAL,
    salaries            REAL,
    expenditure         REAL,
    encumbered          REAL,
    closing_balance     REAL,
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (fund, fy, period, doc_id)
);

-- DESE's own figures for every Massachusetts district: enrollment, staffing FTE, and
-- per-pupil expenditure by function, ACROSS ALL FUNDS. The first view of Lunenburg's
-- school spending in this archive that is neither the town's general fund nor written by
-- the district.
--
-- `reconciles` is DESE's ten printed function components against DESE's own printed
-- in-district total. 16 district-years do not tie -- all charter schools. Lunenburg ties
-- in all 17 years.
CREATE TABLE dese_measure (
    lea                 TEXT NOT NULL,      -- DESE org code; Lunenburg is 01620000
    district            TEXT,
    fy                  INTEGER NOT NULL,
    "group"             TEXT,               -- 'Expenditures Per Pupil', 'Other Staff', ...
    measure             TEXT NOT NULL,
    value               REAL,
    reconciles          TEXT,               -- 'yes' | 'no' | '' (not checkable)
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (lea, fy, "group", measure)
);

-- DESE's spending by FUNCTION CODE, with the general fund and grants/revolving money in
-- SEPARATE columns. Massachusetts DESE dataset `cnfs-edqq`, SY2009-SY2025.
--
-- Rule 11 says the district's budget documents show the general fund and nothing else,
-- so a line rising because a grant ended looks identical to a line rising because the
-- district grew. This is the first published split of the two in this archive. It does
-- NOT close the gap: the split is by FUNCTION CODE, and a function code is not a budget
-- line and not a post.
--
-- `level` IS LOAD-BEARING. The source file puts rollups beside detail and nothing in its
-- column names says which is which; summing every Lunenburg SY2025 row gives
-- $117,996,913 against an in-district total of $27,903,187. NEVER aggregate without
-- filtering `level`, and never add ODTR to OODD -- it is already inside it.
--
--   level='total'     TTPP, the grand total = IIII + OODD
--   level='rollup'    IIII (in-district), OODD (out-of-district)
--   level='category'  the ten in-district categories, plus ODTR and COMM
--   level='detail'    the printed function codes beneath them, plus TUIT, which has
--                     no category row of its own
--
-- `reconciles` is the verdict on the identity that row heads: `yes`, `no`, `partial` for
-- ODTR (whose detail is only ever the single code 9130 and is a component, not the
-- whole), and blank on a detail row, which heads nothing.
--
-- Seven districts only -- Lunenburg and the six peers -- because 363,514 rows would take
-- the published database past Cloudflare's 25MB asset limit. Every other district is in
-- dese_function_statewide as a distribution.
CREATE TABLE dese_function_expenditure (
    fy                  INTEGER NOT NULL,
    lea                 TEXT NOT NULL,      -- DESE org code; Lunenburg is 01620000
    district            TEXT,
    level               TEXT NOT NULL,      -- total | rollup | category | detail
    func_cat_code       TEXT NOT NULL,
    func_cat_desc       TEXT,
    func_code           TEXT NOT NULL,
    func_desc           TEXT,
    in_out_dist         TEXT,               -- blank on every summary row
    gen_fund            REAL,
    grants_revolving    REAL,
    total               REAL,
    per_pupil           REAL,               -- 0 on every out-of-district row; DESE's own
    reconciles          TEXT,
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (lea, fy, func_cat_code, func_code)
);

-- Every Massachusetts district collapsed to a distribution, so a peer comparison has a
-- denominator. One row per year per function per level.
--
-- Rule 6: districts differ in size, grade span and whether they are regional, so a raw
-- dollar comparison between two of them means very little. `per_pupil_median` and the
-- quartiles are the comparable quantity, and `per_pupil_basis` says on every row whether
-- one exists -- DESE prints 0 per pupil against every out-of-district row, and a median
-- of zeros is not a statistic.
--
-- `districts` is the denominator and it INCLUDES charter and virtual districts, which
-- are in DESE's file and are not municipal school districts. Read it before quoting a
-- rank.
CREATE TABLE dese_function_statewide (
    fy                  INTEGER NOT NULL,
    level               TEXT NOT NULL,
    func_cat_code       TEXT NOT NULL,
    func_code           TEXT NOT NULL,
    func_desc           TEXT,
    districts           INTEGER,            -- the denominator, charters included
    gen_fund_total      REAL,
    grants_revolving_total REAL,
    total               REAL,
    grant_share         REAL,               -- grants_revolving_total / total
    per_pupil_basis     TEXT,
    per_pupil_min       REAL,
    per_pupil_p25       REAL,
    per_pupil_median    REAL,
    per_pupil_p75       REAL,
    per_pupil_max       REAL,
    lunenburg_per_pupil REAL,
    lunenburg_rank_of_districts TEXT,       -- '12 of 337', highest first
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (fy, level, func_cat_code, func_code)
);

-- ------------------------------------------------- DESE staffing, students and aid
--
-- Fourteen datasets DESE publishes, loaded here from `sources/data/dese-*.csv`, which are
-- written by three extracts that refuse to write unless the hierarchy each file states
-- still holds. Read those extracts before quoting anything from these tables; the
-- docstrings carry what a column name will mislead you about.
--
-- ONE RULE COVERS ALL OF THEM: **filter on the level column before aggregating.** Every
-- one of these files puts summary rows in the same column space as detail -- a `State`
-- row beside districts, a subject of `All` beside individual subjects, an
-- `All Educators` row beside the reported races -- and nothing in the source's own column
-- names says which is which. Summing a column across such a file counts the same people
-- three or four times.
--
-- AND THEY ARE DIFFERENT GRAINS. A row here is a district-year, or an organisation-year,
-- or a person-class, or a placement cohort, or a town/district pair. They are not
-- joinable into one wide table and were deliberately not written as one.
--
-- `printing` APPEARS ON THREE OF THEM AND IS PART OF THE KEY. DESE publishes the same
-- natural key twice in `dese_sped_indicator`, `dese_sped_program` and
-- `dese_teacher_grade_subject`, for three different reasons: a row published twice
-- identically; a row published twice with the district under two different NAMES
-- (`Ayer Shirley` and `Ayer Shirley School District` for one org code); and a row
-- published twice with DIFFERENT FIGURES -- 0.0 FTE against 0.2 for one school, one
-- subject, one year. The first load of these tables keyed on the natural key and lost 111
-- rows to INSERT OR REPLACE without a word, which is the shape of defect this repository
-- keeps finding: a load that drops rows looks exactly like data that was never published.
-- So `printing` numbers them, as it does for the balance sheet the annual report prints
-- twice, `load_dese_datasets` refuses to write unless every CSV row arrived, and anything
-- aggregating these tables must collapse on `printing` first.

-- vd2f-ib9q. One row per organisation per year: teacher FTE split four ways.
-- `org_level` is state | district | school | collaborative, in one column.
-- A DISTRICT ROW IS NOT THE SUM OF ITS SCHOOL ROWS -- staff with no school assignment
-- have a district row and no school row, and the gap reaches several hundred FTE in the
-- largest districts. Do not reconstruct one from the other.
CREATE TABLE dese_teacher_program_area (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,      -- DESE district code; Lunenburg is 01620000
    district        TEXT,
    org_code        TEXT NOT NULL,      -- the SCHOOL's code, or the district's own
    org_name        TEXT,
    org_level       TEXT NOT NULL,      -- state | district | school | collaborative
    gen_ed_fte      REAL,
    gen_ed_pct      REAL,
    sped_fte        REAL,               -- falls 18.5 (2008) to 2.0 (2026) in Lunenburg
    sped_pct        REAL,               --   while total_fte holds flat. UNRESOLVED.
    career_tech_fte REAL,
    career_tech_pct REAL,
    el_fte          REAL,
    el_pct          REAL,
    total_fte       REAL,
    comments        TEXT,
    reconciles      TEXT,               -- do the four parts sum to total_fte
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, org_code)
);

-- 4684-cw3t. The same grain again with a subject on it.
-- `teacher_fte` IS AN FTE despite the source calling the column `TCHR_CNT`.
-- `subject_level`: all | group | subject. `Core-All Subjects` and `Total Non-Core
-- Academic Subjects` are GROUPS of the subjects beside them, so the members of this
-- column do not partition and summing them double counts.
CREATE TABLE dese_teacher_subject (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    org_code        TEXT NOT NULL,
    org_name        TEXT,
    org_level       TEXT NOT NULL,
    subject         TEXT NOT NULL,
    subject_level   TEXT NOT NULL,      -- all | group | subject
    teacher_fte     REAL,
    licensed_pct    REAL,
    students_per_teacher REAL,          -- parsed from '11.7 to 1'
    student_teacher_ratio_printed TEXT, -- ...and the sentence DESE actually prints
    experienced_pct REAL,
    teachers_without_license REAL,
    in_field_pct    REAL,
    core_academic_fte REAL,
    core_academic_pct REAL,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, org_code, subject)
);

-- 35yv-uxv5. HOW MANY CLASSES RAN, and how full they were, by school and subject.
-- Lunenburg's rows only; the workbook is 115 MB of every district in the Commonwealth.
--
-- THIS IS THE ONLY TABLE HERE THAT COUNTS WHAT WAS TAUGHT. Everything else about the
-- schools counts people, dollars or children. `tot_clss_cnt` is how many classes RAN in
-- a subject, so a subject with none is a subject nobody ran that year -- which is what
-- makes it a measurement of course offerings rather than the teacher-FTE proxy that
-- cannot tell four Spanish sections from two.
--
-- `sy` AND NOT `fy`, DELIBERATELY. Every other DESE table here is keyed `fy` on the
-- SCHOOL YEAR ENDING, and SY2025 in this table is the same year as fy=2025 in
-- `dese_teacher_subject`. The column keeps the publisher's own name because that is what
-- the workbook prints and rule 13 says quote the source, never your rendering of it; the
-- equivalence is stated here so a join can be written without guessing.
--
-- THREE THINGS MUST BE SPLIT ON BEFORE ANYTHING IS SUMMED.
--   `org_type`  District | School. The district row is a ROLLUP of the school rows.
--   `subj`      `All` is a rollup of the 25 named subjects beside it.
--   `CH74 - `   fifteen subjects prefixed this way are Chapter 74 vocational programme
--               areas -- a SECOND, PARALLEL classification, not part of the subject
--               total. Every Lunenburg row is zero: this district runs no Chapter 74
--               programme, and its vocational students go to Monty Tech.
--
-- AND THE THREE FIGURE COLUMNS ARE THREE DIFFERENT QUANTITIES.
--   tot_clss_cnt  classes that ran
--   avg_clss_cnt  DESE's own average class size -- seats over classes
--   tot_stu_cnt   DISTINCT students who took the subject, NOT seats. It is not
--                 tot_clss_cnt * avg_clss_cnt, and on most rows it is far smaller.
--
-- The demographic columns are PERCENTAGES OF THE SUBJECT'S STUDENTS and overlap each
-- other: race, sex, English learner, low income and disability all describe the same
-- children. Nothing here may be added across them.
CREATE TABLE dese_class_size (
    kind            TEXT NOT NULL,      -- always 'class_size'; the extract's own tag
    sy              INTEGER NOT NULL,   -- SCHOOL YEAR ENDING. SY2025 == fy 2025 elsewhere
    org_code        TEXT NOT NULL,
    org_name        TEXT,
    org_type        TEXT NOT NULL,      -- District | School  <- the rollup guard
    subj            TEXT NOT NULL,      -- 'All' is a rollup; 'CH74 - *' is a second scheme
    tot_clss_cnt    REAL,               -- classes that RAN
    avg_clss_cnt    REAL,               -- DESE's own average class size
    tot_stu_cnt     REAL,               -- DISTINCT students, not seats
    aian_pct        REAL,
    as_pct          REAL,
    baa_pct         REAL,
    hl_pct          REAL,
    mnhl_pct        REAL,
    nhpi_pct        REAL,
    wh_pct          REAL,
    fe_pct          REAL,
    ma_pct          REAL,
    el_pct          REAL,
    li_pct          REAL,
    ecd_pct         REAL,
    swd_pct         REAL,
    PRIMARY KEY (sy, org_code, subj)
);

-- 77fu-a6h8. The same grain, with the FTE split across grade bands -- which is what makes
-- it worth 133 MB: grade detail AND FTE, where the town's rosters give grade detail with
-- no FTE and DESE elsewhere gives FTE with no grade.
-- `agrees_with_teacher_subject` is written only on the `All` rows and records whether
-- this dataset and 4684-cw3t state the same total FTE for that organisation. Where they
-- do not, BOTH are kept and neither corrects the other.
CREATE TABLE dese_teacher_grade_subject (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    org_code        TEXT NOT NULL,
    org_name        TEXT,
    org_level       TEXT NOT NULL,
    subject         TEXT NOT NULL,
    subject_level   TEXT NOT NULL,
    pk_2_fte        REAL,
    grade_3_5_fte   REAL,
    grade_6_8_fte   REAL,
    grade_9_12_fte  REAL,
    multi_grade_fte REAL,
    all_grade_fte   REAL,
    total_fte       REAL,
    printing        INTEGER NOT NULL,   -- see below
    reconciles      TEXT,               -- do the six bands sum to total_fte
    agrees_with_teacher_subject TEXT,   -- yes | no | blank; `All` rows only
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, org_code, subject, printing)
);

-- fz9c-2g33. HEADCOUNT, not FTE, and the only DESE table here that counts
-- administrators and paraprofessionals as people. SY2021-SY2023 only.
-- `race_level` is all | detail: `All Educators` is the total row and the seven reported
-- categories are beneath it. There is NO all-job-classes row, so a district total is the
-- sum over the five job classes of the `All Educators` rows and nothing published states
-- it.
CREATE TABLE dese_educator_workforce (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    race_ethnicity  TEXT NOT NULL,
    race_level      TEXT NOT NULL,      -- all | detail
    job_class       TEXT NOT NULL,      -- Administrator | Teacher | Paraprofessional |
                                        --   Other - Licensed | Other - Non-Licensed
    educators_headcount REAL,
    educators_pct   REAL,
    hires_headcount REAL,
    hires_pct       REAL,
    retained_headcount REAL,
    retained_pct    REAL,
    reconciles      TEXT,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea, race_ethnicity, job_class)
);

-- t8td-gens. The denominator for nearly everything else here: enrollment by grade and by
-- selected population, per organisation, back to SY1992.
-- `swd_cnt` is a PUBLISHED count of students with disabilities per organisation. It is
-- not the same quantity as the count in dese_sped_program, which is measured on a
-- different date and includes out-of-district children -- the two differ and the
-- difference is not reconciled anywhere.
CREATE TABLE dese_enrollment (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    org_code        TEXT NOT NULL,
    org_name        TEXT,
    org_level       TEXT NOT NULL,
    total_cnt       REAL,
    pk_cnt REAL, k_cnt REAL,
    grade_1_cnt REAL, grade_2_cnt REAL, grade_3_cnt REAL, grade_4_cnt REAL,
    grade_5_cnt REAL, grade_6_cnt REAL, grade_7_cnt REAL, grade_8_cnt REAL,
    grade_9_cnt REAL, grade_10_cnt REAL, grade_11_cnt REAL, grade_12_cnt REAL,
    sp_cnt          REAL,               -- special education beyond grade 12
    el_cnt REAL, el_pct REAL,
    first_lang_not_english_cnt REAL,
    high_needs_cnt REAL, high_needs_pct REAL,
    low_income_cnt REAL, low_income_pct REAL,
    econ_disadvantaged_cnt REAL, econ_disadvantaged_pct REAL,
    swd_cnt REAL, swd_pct REAL,
    reconciles      TEXT,               -- do PK..12 plus SP sum to total_cnt
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, org_code)
);

-- yamx-769q. Special education indicators: the context counts, the staffing ratios, and
-- the outcome and assessment measures, by grade group and student group.
-- `grades_level` is all | subset and THE SUBSETS OVERLAP. `Grade 10` is inside
-- `Grades 9-12` is inside `K-12`, and `Grades 3-8` crosses both. There is no sum of them
-- that means anything.
-- `denominator_cnt` is the population the percentage is OF. It is not the indicator's own
-- count -- that is `measure_cnt`.
-- `value_type` says whether a row is a percentage, an average, an FTE or an FTE per 100
-- students with disabilities. Read it before doing arithmetic on `measure_cnt`.
CREATE TABLE dese_sped_indicator (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    geo_level       TEXT NOT NULL,      -- state | district
    grades          TEXT NOT NULL,
    grades_level    TEXT NOT NULL,      -- all | subset (the subsets OVERLAP)
    student_group   TEXT NOT NULL,
    student_group_level TEXT NOT NULL,  -- all | detail
    indicator_category TEXT NOT NULL,
    indicator       TEXT NOT NULL,
    printing        INTEGER NOT NULL,   -- see below
    denominator_cnt REAL,
    measure_cnt     REAL,
    measure_pct     REAL,
    value_type      TEXT,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea, grades, student_group, indicator_category, indicator, printing)
);

-- n62c-bx65. What the students with disabilities are: disability type, demographics,
-- placement, and the special education FTE ratios.
-- `indicator_level` is total | member. Each category carries its own total row.
-- THREE CATEGORIES BEHAVE DIFFERENTLY AND THE EXTRACT PRINTS WHICH ON EVERY RUN:
--   Placement runs SHORT of its own total, because its four members are IN-DISTRICT
--     placements and children placed out of district are in the total and in none of them.
--   Disability Type is a COLLAPSED rendering of Disability Type All, with several
--     disabilities folded into `Other Disability`. Adding the two counts every child twice.
--   Special Education FTEs per 100 SWDs is a RATIO, not a count, even though it sits in
--     the same column and `value_type` says `Percent` on every row in this file.
CREATE TABLE dese_sped_program (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    geo_level       TEXT NOT NULL,
    indicator_category TEXT NOT NULL,
    indicator       TEXT NOT NULL,
    indicator_level TEXT NOT NULL,      -- total | member
    printing        INTEGER NOT NULL,   -- see below
    denominator_cnt REAL,
    measure_cnt     REAL,
    measure_pct     REAL,
    value_type      TEXT,
    reconciles      TEXT,               -- do the members sum to the category's own total
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea, indicator_category, indicator, printing)
);

-- 92x3-2qj9. Where a cohort started and where the same children are now. THE BASES ARE
-- TINY: a Lunenburg cohort is tens of children, so a percentage here must never travel
-- without its count. `unaccounted_cnt` is the cohort less the four destinations -- what
-- it IS (moved away, private school, aged out, suppressed) is not established.
CREATE TABLE dese_sped_trajectory (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    geo_level       TEXT NOT NULL,
    grade_span      TEXT NOT NULL,      -- K-12 and K-2 OVERLAP; never sum them
    placement_at_start TEXT NOT NULL,
    cohort_cnt      REAL,
    no_iep_cnt REAL, no_iep_pct REAL,
    included_cnt REAL, included_pct REAL,
    sub_separate_cnt REAL, sub_separate_pct REAL,
    out_of_district_cnt REAL, out_of_district_pct REAL,
    unaccounted_cnt REAL,
    reconciles      TEXT,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea, grade_span, placement_at_start)
);

-- 8aww-sugs. Caseload movement: who entered and who left special education services.
-- TWO THINGS BEFORE ANYBODY QUOTES IT.
--   `repeats_prior_year` is `yes` where every one of the four figures exactly equals the
--   same district's previous year. Lunenburg's SY2024 and SY2025 are such a pair. Four
--   independent counts landing identically two years running is not plausible and a row
--   carried forward is; nothing may sum two such years as two years of movement.
--   `grade_rows_sum` is on the K-12 rows and is the sum of that district's grade rows. IT
--   DOES NOT EQUAL `enrolled_cnt`, and the grade rows are NOT the K-12 row broken down:
--   the `Grade 12` row is a fraction of the size of the others, so a grade row counts
--   children still enrolled to be observed. What the residual IS is not established.
CREATE TABLE dese_sped_movement (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    geo_level       TEXT NOT NULL,
    grades          TEXT NOT NULL,
    grades_level    TEXT NOT NULL,      -- all | grade
    enrolled_cnt    REAL,
    on_iep_cnt      REAL,
    moved_in_cnt    REAL,
    moved_out_cnt   REAL,
    grade_rows_sum  REAL,               -- K-12 rows only; NOT equal to enrolled_cnt
    repeats_prior_year TEXT,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea, grades)
);

-- vxt3-k35x AND 8xyg-59b2 -- ONE table, because the two datasets hold the IDENTICAL rows
-- and differ only in column order. The extract compares them tuple by tuple on every run
-- and refuses to load if they ever diverge.
-- Read it in either direction: filter on `town` for where a town's resident children go,
-- filter on `lea` for who arrives at a district and from where.
-- Both dataset ids are carried, because a reader checking the figure needs to know that
-- the two published files are one measurement rather than two agreeing ones.
CREATE TABLE dese_town_enrollment (
    fy              INTEGER NOT NULL,
    town            TEXT NOT NULL,      -- town of RESIDENCE
    enrollment_reason TEXT NOT NULL,    -- School Choice Program, Charter School,
                                        --   Resident/Member, tuitioned in several ways
    lea             TEXT NOT NULL,      -- the district the children actually attend
    district        TEXT,
    students        REAL,
    doc_id_sending  TEXT NOT NULL,
    doc_id_receiving TEXT NOT NULL,
    PRIMARY KEY (fy, town, enrollment_reason, lea)
);

-- The Chapter 70 formula, FY1993-FY2026, from the DESE district profile workbook.
-- THREE COLUMN NAMES IN THE SOURCE MEAN TWO THINGS EACH AND ARE SPLIT HERE:
--   `required_nss`           column I: the formula's arithmetic, = rlc + aid
--   `required_nss_published` column J: what DESE publishes, carryover included. These are
--                            NOT equal -- they differ in over a thousand district-years.
--   `ch70_aid` / `ch70_aid_after_penalties`: columns H and M, the second described by the
--                            sheet as reflecting penalties.
-- `nss_stage` IS LOAD-BEARING. The source column is headed `actualNSS` for all 34 years,
-- and for FY2025 and FY2026 the value is BUDGETED net school spending -- the sheet's own
-- DataNSS names them `budnss`. Rule 1: a rate measured from an actual to a budget is
-- partly growth and partly the step between the two. Filter on `nss_stage` or say which
-- you mean.
CREATE TABLE dese_ch70_formula (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,      -- 8-digit DESE code, joinable to every table above
    org4_code       TEXT NOT NULL,      -- the workbook's own 4-digit key
    lea_number      TEXT,
    district        TEXT,
    level           TEXT NOT NULL,      -- state | district
    foundation_enrollment REAL,
    foundation_budget REAL,
    required_local_contribution REAL,
    ch70_aid        REAL,
    ch70_aid_after_penalties REAL,
    required_nss    REAL,               -- column I, computed
    required_nss_published REAL,        -- column J, published, includes carryover
    net_school_spending REAL,
    nss_stage       TEXT,               -- actual | budgeted -- READ THIS
    nss_pct_of_required REAL,
    reconciles      TEXT,               -- required_nss == rlc + aid
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, org4_code)
);

-- The aid build-up, term by term, FY2007 on. Every increment the formula adds and every
-- reduction it applies, between the foundation budget and the aid actually paid.
CREATE TABLE dese_ch70_aid_factor (
    fy              INTEGER NOT NULL,
    lea             TEXT NOT NULL,
    district        TEXT,
    level           TEXT NOT NULL,
    foundation_enrollment REAL,
    foundation_budget REAL,
    required_local_contribution REAL,
    target_aid_pct  REAL,
    foundation_aid_increment REAL,
    down_payment_aid_increment REAL,
    growth_aid_increment REAL,
    target_aid_phase_in REAL,
    minimum_aid_increment REAL,
    non_operating_reduction REAL,
    ch70_aid        REAL,
    required_nss    REAL,
    ch70_aid_reduction REAL,
    hold_harmless_low_income REAL,
    minimum_aid_adjustment REAL,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea)
);

-- The MUNICIPAL side of the same formula, and a DIFFERENT GRAIN: a row is a town, not a
-- district. For a regional district several towns contribute to one district and the two
-- tables must not be joined one to one. This is where the town's ability to pay is
-- computed -- equalized valuation, income, and the effort each implies.
CREATE TABLE dese_ch70_contribution (
    fy              INTEGER NOT NULL,
    lea_number      TEXT NOT NULL,      -- the workbook's municipal key, NOT a DESE code
    municipality    TEXT,
    equalized_valuation REAL,
    property_local_effort REAL,
    income          REAL,
    income_local_effort REAL,
    combined_effort_yield REAL,
    town_foundation_enrollment REAL,
    town_foundation_budget REAL,
    target_local_contribution REAL,
    municipal_revenue_growth_factor REAL,
    preliminary_contribution REAL,
    excess_effort   REAL,
    effort_reduction REAL,
    shortfall       REAL,
    dollar_increment REAL,
    acceleration    REAL,
    required_local_contribution REAL,
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea_number)
);

-- Every Massachusetts district collapsed to a distribution, so a peer comparison has a
-- denominator. The row-level Chapter 70 tables above are Lunenburg, its six peers and the
-- state row -- the published database has to fit under Cloudflare's 25 MB per-asset limit
-- -- and this is what a reader would otherwise lose: where Lunenburg SITS.
--
-- `basis` says on every row what the ratio is a ratio OF. Read it: foundation enrollment
-- is not a headcount of the children in the buildings, and the circuit breaker rows are
-- keyed on a fiscal year the others are not.
--
-- Publish the share-of-required as a MEASUREMENT and never as a verdict. Both readings are
-- true at once -- the town spends well above what the state requires, AND the required
-- minimum is a floor rather than a standard of adequacy -- and a page giving one without
-- the other is taking a side using a number.
CREATE TABLE dese_ch70_statewide (
    fy              INTEGER NOT NULL,
    measure         TEXT NOT NULL,
    basis           TEXT,               -- what the ratio is OF
    districts       INTEGER,            -- the denominator; read it before quoting a rank
    p_min REAL, p25 REAL, median REAL, p75 REAL, p_max REAL,
    lunenburg       REAL,
    lunenburg_rank_of_districts TEXT,   -- '12 of 337', highest first
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, measure)
);

-- ab34-d3ma. Reimbursement for high-cost special education placements.
-- **KEYED ON FY, NOT SY.** Every other DESE table here is school year. This repository has
-- already had a fiscal-year type error that matched nothing silently.
-- `eligible_students_claimed` is a count of CHILDREN, which is rare in this archive.
-- This is money the district RECEIVES and it is not in the general fund appropriation the
-- town votes. Rule 11: a budget line that fell because circuit breaker rose is not a line
-- that got cheaper.
CREATE TABLE dese_circuit_breaker (
    fy              INTEGER NOT NULL,   -- FISCAL year, not school year
    lea             TEXT NOT NULL,
    district        TEXT,
    level           TEXT NOT NULL,      -- state | district
    eligible_students_claimed REAL,     -- CHILDREN, not dollars
    total_eligible_expenses REAL,
    threshold_amount REAL,
    net_eligible_instruction_tuition REAL,
    net_eligible_transport REAL,
    total_net_claim REAL,
    reimb_instruction_tuition REAL,
    reimb_special_circumstance_tuition REAL,
    reimb_transport REAL,
    reimb_special_circumstance_transport REAL,
    prior_year_adjustment REAL,
    total_quarterly_payment REAL,
    extra_relief_payment REAL,
    additional_supplemental_payment REAL,
    comments        TEXT,
    reconciles      TEXT,               -- tuition claim + transport claim == total claim
    doc_id          TEXT NOT NULL,
    PRIMARY KEY (fy, lea)
);

-- Figures the town or district stated about itself, in public, with the quote.
--
-- These are NOT ours and are not computed from anything here. They exist because the
-- most important number about FY25 -- the surplus -- is one the town arrived at by
-- closing its books, which we cannot do from what we hold. Recording it as a stated
-- figure, with who said it and the raw sentence, keeps the distinction that rule 13
-- exists for: this is quoted, not derived.
CREATE TABLE stated_figure (
    fy                  INTEGER NOT NULL,
    metric              TEXT NOT NULL,
    amount              REAL NOT NULL,
    stated_on           TEXT,               -- the date it was said
    stated_by           TEXT,
    basis               TEXT,               -- 'close' | 'estimate' | 'preliminary'
    doc_id              TEXT NOT NULL,
    source_ref          TEXT,               -- the line or cell it is quoted from
    quote               TEXT NOT NULL,      -- the raw sentence
    supersedes          REAL,               -- an earlier figure this replaced
    note                TEXT,
    PRIMARY KEY (fy, metric, amount)
);

-- Grants as the district's own budget documents list them, by year and owner.
-- An amount here is what a document says was awarded. It is NOT a mapping onto the
-- operating lines the grant paid for -- that mapping is exactly what nobody publishes,
-- and the Town's own 1 September 2026 statement about $287,000 of out-of-district
-- tuition charged to the FY26 IDEA grant is the first instance of it being named at all.
CREATE TABLE grant_award (
    fy                  TEXT NOT NULL,
    kind                TEXT,               -- federal | state
    name                TEXT NOT NULL,
    amount              REAL,
    owner               TEXT,
    documents_disagree  INTEGER DEFAULT 0,
    doc_id              TEXT,
    url                 TEXT,
    sha256              TEXT,
    PRIMARY KEY (fy, name)
);

CREATE INDEX ix_account_function ON account(function);
CREATE INDEX ix_ledger_fy      ON ledger_snapshot(fy, period);
CREATE INDEX ix_ledger_account ON ledger_snapshot(account_id);
CREATE INDEX ix_budget_fy      ON budget_figure(fy, stage);
CREATE INDEX ix_budget_line    ON budget_figure(line_key);
CREATE INDEX ix_workbook_line  ON workbook_figure(line_key, fy);
"""

# The MUNIS fiscal calendar. Period 13 is the year-end close, after purchase orders are
# closed out in the lapse period -- the step that moved the FY25 surplus from
# $582,115.44 on 3 September 2025 to $603,885.97 on 17 September 2025.
PERIODS = [
    (1, 'July', 1, 0), (2, 'August', 2, 0), (3, 'September / Q1', 3, 0),
    (4, 'October', 4, 0), (5, 'November', 5, 0), (6, 'December / Q2', 6, 0),
    (7, 'January', 7, 0), (8, 'February', 8, 0), (9, 'March / Q3', 9, 0),
    (10, 'April', 10, 0), (11, 'May', 11, 0), (12, 'June', 12, 0),
    (13, 'Year-end close (after lapse period)', 12, 1),
]

# lps-budget-lines.csv is the FY27 workbook flattened wide. Each column is a year and a
# kind, and the kinds are the workbook's own headers (row 4 / row 5 of the sheet).
WORKBOOK_COLUMNS = {
    'fy23_actual':          (2023, 'actual'),
    'fy24_actual':          (2024, 'actual'),
    'fy25_actual':          (2025, 'actual'),
    'fy25_budget':          (2025, 'budget'),
    'fy26_final':           (2026, 'final_budget'),
    'fy26_actual_td':       (2026, 'actual_to_date'),
    'fy26_encumb_td':       (2026, 'encumbered_to_date'),
    'fy27_restoration':     (2027, 'restoration_proposed'),
    'fy27_core':            (2027, 'core_proposed'),
    'fy27_level_service':   (2027, 'level_service_proposed'),
    'fy27_balanced':        (2027, 'balanced_proposed'),
    'restoration_2_24_26':  (2027, 'restoration_2_24_26'),
    'forecast_outyear':     (2029, 'forecast'),
}

# Reference tables loaded as they stand. These are not the analytical spine; they are the
# domain data the model already reads, put where it can be joined rather than re-parsed.
REFERENCE = [
    'athletic-fee-schedule', 'athletics-by-sport', 'athletics-by-sport-reconciliation',
    'athletics-history', 'capital-funding-history', 'capital-plan-fy27',
    'free-cash-proof', 'fund-1301-cash-journal', 'ood-tuition-history',
    'line-history-disagreements', 'rate-register', 'sped-para-history',
    'sped-teacher-history', 'sped-transport-history', 'total-expenses-history',
    'total-salaries-history', 'variance-by-group',

    # From the annual town reports, FY2011-FY2025. See plans/ANNUAL-REPORTS.md.
    #
    # Two of these answer standing questions this project had recorded as unanswerable,
    # and both were in documents already held: `placement-counts` is the count of children
    # placed outside the district, which no budget line can produce, and
    # `ballot-questions` is the record of what the town was actually asked to fund and
    # whether it agreed.
    #
    # `annual-report-catalogue` is not data about the town -- it is data about the
    # documents, 819 blocks found by reading all sixteen reports end to end rather than by
    # searching them. It carries each table's PRINTED heading, because the headings differ
    # between years and that is precisely what defeats a search.
    #
    # `annual-report-receipts` carries a `status` column on every row: `reconciled` means
    # the year ties to its own printed GRAND TOTAL twice over, `partial` means it does not
    # and cannot. **Never aggregate across years without splitting on it.**
    # Every reduction and restoration the district NAMED in one of its own budget
    # documents, quoted at a page. Rule 13a: every row is `stated` — a document somebody
    # assembled to argue for a budget — and none of it is evidence that a post was
    # removed. `operative` on the report payload, not here, marks which list each cycle
    # actually adopted. See scripts/extract_stated_cuts.py.
    'stated-cuts',

    'placement-counts', 'ballot-questions', 'annual-report-receipts',
    'annual-report-catalogue', 'annual-report-contents', 'annual-report-survey',
    'staff-roster-entries', 'staff-roster-counts', 'report-anomalies',
    'extraction-plan', 'special-revenue-funds',

    # The generic extraction, one table per family. Every row carries `status` and
    # `reconciliation`: `reconciled` means the rows tie to the total the report itself
    # prints, column by column; `partial` means they do not, and the residual is on the
    # row. **Nothing here may be aggregated without splitting on `status` first.**
    #
    # Most of these are currently partial. The rows are real -- read at their own position,
    # in the column they were printed in -- but an unreconciled extract is a transcription,
    # not a verified figure, and rule 13 governs what may be quoted.
    'report-appropriations', 'report-trust-funds', 'report-debt',
    'report-capital-projects', 'report-valuation', 'report-elections',
    'report-officials', 'report-dept-activity', 'report-enrollment-mcas',
    'report-monty-tech', 'report-gross-wages', 'report-vital-records',
]

VIEWS = """
-- Budget against the town's books, by function code. THE ONE JOIN BETWEEN THE TWO SIDES.
--
-- A view rather than rows in `crosswalk`, deliberately. The function code joins a
-- CATEGORY -- 2710 Guidance -- and never a line: MUNIS truncates account names to ten
-- characters, so `MS GUIDANC` and `HS GUIDANC` are both 2710 and cannot be told apart
-- from each other, while the budget has a row per school. Writing that into `crosswalk`
-- would record an inference as a mapping. Here it is computed, and what it is computed
-- from is visible in the SQL.
--
-- Coverage is narrow and does not widen by wanting it to: `account.function` is
-- populated only where the source was a SPREADSHEET export. That is FY2026 period 12.
CREATE VIEW v_function_budget_vs_ledger AS
SELECT  a.function                                  AS function_code,
        l.fy, l.period,
        SUM(l.revised)                              AS ledger_revised,
        SUM(l.expended)                             AS ledger_expended,
        SUM(l.encumbered)                           AS ledger_encumbered,
        COUNT(DISTINCT a.account_id)                AS accounts,
        (SELECT COUNT(*) FROM budget_line b
          WHERE substr(b.function_group, 1, 4) = a.function) AS budget_lines,
        l.doc_id
FROM    ledger_snapshot l
JOIN    account a USING (account_id)
WHERE   a.function IS NOT NULL AND a.account_type = 'expense'
GROUP BY a.function, l.fy, l.period;


-- Did we spend what we appropriated? One row per account per closed year.
-- Only period 13 -- an interim period answers a different question.
CREATE VIEW v_appropriation_vs_spend AS
SELECT  l.fy, a.fund, a.dept, a.name, a.level,
        l.original, l.transfers, l.revised, l.expended, l.encumbered,
        l.available                              AS surplus,
        ROUND(l.available * 100.0 / NULLIF(l.revised, 0), 2) AS surplus_pct,
        l.doc_id
FROM    ledger_snapshot l JOIN account a USING (account_id)
WHERE   l.period = 13;

-- How a line moved during the year. Transfers are cumulative in the report, so the
-- movement between two periods is the difference, not the later value.
--
-- EXPENSE ACCOUNTS ONLY. Revenue is stored NEGATIVE in `ledger_snapshot`, and 224 revenue
-- rows sat in here unnegated and unlabelled -- so anything ranking or summing this got
-- revenue mixed into an expense measure. `account_type` is the discriminator and it was
-- simply never applied.
--
-- `moved_since_last` IS NOT COMPUTABLE FROM THE DATA WE HOLD, and is kept only so the
-- shape does not change under anything reading it. The LAG needs one account at two
-- periods; the ledger holds period 9 (71 department roll-ups + 277 accounts) and period
-- 12 (a different 635), and NO account_id appears in both. It was non-NULL on 2 of 983
-- rows, and both were duplicate rows WITHIN period 9 rather than movement between
-- periods -- which is worse than empty, because two plausible numbers read as data.
-- It is now NULL always and says so. Closing it needs the same accounts printed at two
-- periods of one fiscal year: a MUNIS year-to-date budget report at p09 AND p12 for the
-- same FY.
CREATE VIEW v_transfer_history AS
SELECT  a.dept, a.name, l.fy, l.period, l.original, l.transfers, l.revised,
        CAST(NULL AS REAL)                                          AS moved_since_last,
        l.doc_id
FROM    ledger_snapshot l JOIN account a USING (account_id)
WHERE   a.account_type = 'expense'
ORDER BY a.dept, l.fy, l.period;

-- Burn rate: what share of the revised budget is committed, against how much of the year
-- has gone. NOT a surplus prediction on its own -- school spending is seasonal, so a
-- deviation only means something against that account's own history in prior years.
-- That baseline needs FY24 and FY25 at multiple periods, which is what was requested.
CREATE VIEW v_burn AS
SELECT  a.dept, a.name, l.fy, l.period,
        p.months_elapsed / 12.0                                     AS year_elapsed,
        l.expended / NULLIF(l.revised, 0)                           AS spent_share,
        (l.expended + l.encumbered) / NULLIF(l.revised, 0)          AS committed_share,
        (l.expended + l.encumbered) / NULLIF(l.revised, 0)
            - p.months_elapsed / 12.0                               AS pace_gap,
        l.available                                                 AS available_now,
        l.doc_id
FROM    ledger_snapshot l
        JOIN account a USING (account_id)
        JOIN fiscal_period p ON p.period = l.period
WHERE   p.is_final = 0
        -- EXPENSE ACCOUNTS ONLY. Revenue is stored NEGATIVE and was neither filtered nor
        -- negated here, so 224 revenue rows carried a `spent_share` that is arithmetic on
        -- a sign rather than a burn rate. The published question "which departments are
        -- spending faster than the year is elapsing?" answered PS TUITION, PARK FINE and
        -- DOG FINES -- none of them a department, none of them spending. Their `dept` was
        -- NULL, which was the tell nobody read.
        AND a.account_type = 'expense';

-- Budget against actual for a single line, from the district's own documents.
-- Both halves are read from the same document, which is what makes the pair sound;
-- these lines do NOT sum back to the district totals, so never apportion with this.
CREATE VIEW v_line_budget_vs_actual AS
SELECT  b.line_key, b.label, b.fy,
        MAX(CASE WHEN b.stage = 'settled'  THEN b.value END) AS settled,
        MAX(CASE WHEN b.stage = 'proposed' THEN b.value END) AS proposed,
        MAX(CASE WHEN b.stage = 'restated' THEN b.value END) AS actual,
        MAX(b.documents_disagree)                            AS documents_disagree
FROM    budget_figure b
-- variant = '' or a scenario column would win the MAX and be reported as the year's
-- budget. A document stating four FY27 proposals states four figures, not one.
WHERE   b.variant = ''
GROUP BY b.line_key, b.label, b.fy;

-- WHAT EACH DOCUMENT SAYS ABOUT A CONTESTED LINE, and which statement the ordering kept.
--
-- `budget_figure.documents_disagree` is a flag, and a flag is the least a reader can be
-- told. The completeness matrix called a year `partial` on the strength of it and could
-- not say whether that meant one line out of 282 or a third of the year -- and the losing
-- figure had been discarded at extraction, so nothing could show the disagreement even if
-- it wanted to. The cell could name the winner and no more.
--
-- Nothing here decides which document is right. Two documents stating a line differently
-- is a fact about the documents; choosing between them is not a fact at all.
CREATE VIEW v_budget_disagreement AS
SELECT  d.fy, d.stage, d.variant, d.key AS line_key, d.label,
        d.source, CAST(d.value AS REAL) AS value,
        CAST(d.is_kept AS INTEGER) AS is_kept,
        CAST(d.spread AS REAL) AS spread, d.kind
FROM    line_history_disagreements d;

-- The scenarios, kept separate and named. `final-budget-document.txt` prints Restoration,
-- Core Budget and Balanced side by side for FY27, and which of them became the budget is
-- a fact about a vote rather than about this document.
CREATE VIEW v_budget_scenario AS
SELECT  b.line_key, b.label, b.fy, b.stage, b.variant, b.value, b.doc_id
FROM    budget_figure b
WHERE   b.variant <> '';

-- The same question off the FY27 workbook, which is the only source with both halves
-- of FY25. A restatement, not a ledger: `document.basis` says so.
CREATE VIEW v_workbook_budget_vs_actual AS
SELECT  bud.line_key, bud.row, bud.fy,
        bud.value AS budget, act.value AS actual,
        bud.value - act.value AS under_budget
FROM    workbook_figure bud
        JOIN workbook_figure act
          ON act.row = bud.row AND act.fy = bud.fy AND act.doc_id = bud.doc_id
         AND act.column_kind = 'actual'
WHERE   bud.column_kind IN ('budget', 'final_budget')
  AND   bud.row_kind = 'line';

-- Where the money comes from. Revenue is stored as MUNIS prints it -- negative -- so
-- it is negated here to read as an inflow, and only here, once, visibly.
CREATE VIEW v_revenue AS
SELECT  a.fund, f.name AS fund_name, a.org, a.object, a.name, l.fy, l.period,
        -l.original AS budgeted, -l.revised AS revised, -l.expended AS received,
        -l.available AS still_to_come,
        ROUND(l.expended * 100.0 / NULLIF(l.revised, 0), 1) AS pct_received,
        l.doc_id
FROM    ledger_snapshot l
        JOIN account a USING (account_id)
        LEFT JOIN fund f ON f.fund = a.fund
WHERE   a.account_type = 'revenue';

-- Money arriving from another fund. These accounts ARE the mechanism by which a
-- revolving fund, an enterprise fund or free cash reaches the operating budget, and
-- they are the only place that movement is visible from the general fund side.
CREATE VIEW v_interfund AS
SELECT  * FROM v_revenue
WHERE   object LIKE '490%' OR object = '499900';

-- State aid as the town has actually booked it, against what it budgeted. Chapter 70 is
-- object 450600. Rule 11: this is the revenue side the expense side cannot see.
CREATE VIEW v_state_aid AS
SELECT  * FROM v_revenue WHERE object LIKE '45%';

-- What each fund took in and spent, beside its balance. A fund balance rolls forward;
-- a department appropriation lapses. Never read the two as the same quantity.
CREATE VIEW v_fund_year AS
SELECT  fa.fund, f.name, f.kind, f.restriction, fa.fy, fa.period,
        fa.revenue, fa.salaries + fa.expenditure AS spent,
        fa.closing_balance, fa.doc_id
FROM    fund_activity fa LEFT JOIN fund f ON f.fund = fa.fund;

-- Every figure with its address attached. If a query cannot produce this, the figure
-- should not be published.
CREATE VIEW v_provenance AS
SELECT 'ledger' AS fact, l.doc_id, d.path, d.basis, d.copy_state, COUNT(*) AS rows
FROM   ledger_snapshot l LEFT JOIN document d ON d.doc_id = l.doc_id GROUP BY l.doc_id
UNION ALL
SELECT 'budget', b.doc_id, d.path, d.basis, d.copy_state, COUNT(*)
FROM   budget_figure b LEFT JOIN document d ON d.doc_id = b.doc_id GROUP BY b.doc_id
UNION ALL
SELECT 'workbook', w.doc_id, d.path, d.basis, d.copy_state, COUNT(*)
FROM   workbook_figure w LEFT JOIN document d ON d.doc_id = w.doc_id GROUP BY w.doc_id;
"""


def rows(name):
    path = os.path.join(DATA, name + '.csv')
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def num(v):
    """A figure, or None. Blank, '-' and '.00'-style placeholders are not zero."""
    if v is None:
        return None
    v = str(v).strip().replace(',', '').replace('$', '')
    if v in ('', '-', '--', 'n/a', 'None'):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def key(label):
    """Normalise a printed line name. Matches extract_line_history.py's convention."""
    return ' '.join(str(label).lower().split())


def load_documents(db):
    """Provenance for every document any fact cites.

    Assembled from four places, because no single one has all of it:

      document-basis.csv     what produced a document's figures, and its hidden columns
      link-status.csv        whether the publisher's copy still opens
      copy-status.csv        whether our bytes still match the publisher's
      sources/*/index.csv    the upstream address and sha256 of crawled sources

    Then every remaining gap is filled by HASHING THE FILE ON DISK. A document row
    without a sha256 is a document a reader cannot verify they have the same copy of,
    which is most of rule 12's point, and 220 files is a second of compute.

    Finally, any doc_id a fact cites that is still unknown gets a stub rather than being
    dropped. An orphaned figure must be visible as orphaned.
    """
    # Both sides of this join, normalised.
    #
    # `link-status.csv` and `copy-status.csv` key on a path relative to `sources/`
    # (`district-budget/docs/x.pdf`) while `document-basis.csv` keys on a repo-relative
    # one (`sources/district-budget/docs/x.pdf`). They have never matched, so every one of
    # the 616 document rows carried NULL for `link_state` and `copy_state` -- the two
    # columns that say whether the publisher's copy still opens and whether it still
    # matches ours. /api/documents published those nulls, and llms.txt described the field
    # as telling you exactly that.
    #
    # A join that silently matches nothing looks identical to data that is simply absent.
    def keyed(name):
        out = {}
        for r in rows(name):
            p = (r.get('path') or '').strip()
            if not p:
                continue
            out[p] = r
            out[p if p.startswith('sources/') else 'sources/' + p] = r
        return out

    link = keyed('link-status')
    copy = keyed('copy-status')

    # The crawlers' own indexes carry the upstream URL and the sha256 taken at fetch time.
    # Every mirror's index, not a named three. The list read `state-dese`,
    # `district-budget`, `town-budget` -- written before the town split created
    # `town-supplementary` and `town-annual-reports`, so the upstream URL and sha256 of
    # everything that moved stopped being found. A hardcoded folder list is the same bug
    # that broke build_dataset_provenance.py, in a second place.
    crawled = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'sources', '*', 'index.csv'))):
        with open(path, encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                if r.get('local'):
                    crawled[r['local']] = r

    out = {}
    for r in rows('document-basis'):
        p = r['path']
        lk, cp, cr = link.get(p, {}), copy.get(p, {}), crawled.get(p, {})
        out[p] = [p, p, r.get('source_type'), r.get('basis'), r.get('ledger_at'),
                  r.get('hidden_columns'),
                  lk.get('url') or cp.get('url') or cr.get('upstream'),
                  lk.get('code'), cp.get('state'),
                  cp.get('remote_sha256'),
                  cp.get('local_sha256') or cr.get('sha256')]

    # Crawled sources that document-basis does not classify are still documents.
    #
    # And they get their link and copy state like everything else. This branch passed
    # None for both, which is most of the archive: 613 of 616 document rows carried no
    # answer to "does the publisher's copy still open" or "does it still match ours" --
    # the two questions rule 12 exists to keep answerable. /api/documents published those
    # nulls and llms.txt described the field as telling you exactly that.
    for p, cr in crawled.items():
        if p not in out:
            lk, cp = link.get(p, {}), copy.get(p, {})
            out[p] = [p, p, 'primary', None, None, None,
                      lk.get('url') or cp.get('url') or cr.get('upstream'),
                      lk.get('code'), cp.get('state'),
                      cp.get('remote_sha256'),
                      cp.get('local_sha256') or cr.get('sha256')]

    return out


def finish_documents(db, docs, cited):
    """Fill in the sha256 of anything on disk, stub anything still unknown, and write."""
    for p in sorted(set(cited) - set(docs)):
        docs[p] = [p, p, 'primary', None, None, None, None, None, None, None, None]

    hashed = 0
    for p, row in docs.items():
        if row[10]:
            continue
        full = os.path.join(ROOT, p)
        if os.path.isfile(full):
            h = hashlib.sha256()
            with open(full, 'rb') as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b''):
                    h.update(chunk)
            row[10] = h.hexdigest()
            hashed += 1
    db.executemany('INSERT OR REPLACE INTO document VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   [tuple(v) for v in docs.values()])
    return len(docs), hashed


TOWN_LEDGER_DOC = 'sources/town-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.txt'
WORKBOOK_DOC = 'sources/budget-workbooks/fy27-proposals.xlsx'
FUNDS_DOC = 'sources/budget-workbooks/school-funds-fy26.xlsx'
SPECIAL_REV_DOC = 'sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx'

# Fund kinds, from what the fund's own name and the documents establishing it say. A fund
# whose purpose is not stated in a document we hold is left NULL rather than guessed.
FUND_KIND = {
    '0100': ('GENERAL FUND', 'general', None),
    '1301': ('CHAPTER 658 REVOLVING FUND', 'revolving',
             'M.G.L. c.71 s.47 athletics and student activities'),
    '1308': ('SCHOOL CHOICE REVOLVING', 'revolving', None),
    '1311': ('SCHOOL GIFT FUND', 'gift', None),
    '1312': ('EXTENDED DAY REVOLVING FUND', 'revolving', None),
    '2200': ('SCHOOL LUNCH REVOLVING', 'revolving', None),
    '5000': ('SEWER BETTERMENTS', 'enterprise', None),
    '6100': ('WATER ENTERPRISE FUND', 'enterprise', None),
    '7900': ('SOLID WASTE/RECYCLING ENTERPRISE', 'enterprise', None),
}


def load_munis(db):
    """Every MUNIS year-to-date budget report, from scripts/extract_munis_report.py.

    Expenditures and revenues, general fund and enterprise funds, at whichever grain the
    report was run: `level='account'` where it was run with Print totals only: N, and
    `level='department'` where it was not. Revenue rows keep MUNIS's credit convention
    and are stored NEGATIVE exactly as printed; `account.account_type` says which.
    """
    accounts, facts, funds = {}, [], {}
    for r in rows('munis-ledger'):
        # Never default a missing fund to the general fund: an enterprise account filed
        # under 0100 corrupts every total downstream. The extractor guarantees a fund.
        fund = r['fund']
        if not fund:
            raise ValueError('munis-ledger row with no fund: %r' % r['name'])
        if r['level'] == 'account':
            aid = '%s-%s-%s' % (fund, r['org'], r['object'])
        else:
            aid = '%s-%s' % (fund, r['dept'])
        fy = int(r['fy'])
        # '0000' is MUNIS's filler for an account with no function -- town departments,
        # and every row from a printed report. Store NULL rather than a code that looks
        # real and joins to nothing.
        fn = (r.get('function') or '').strip() or None
        if fn == '0000':
            fn = None
        accounts[aid] = (aid, fund, r['fund_name'], r['dept'] or None,
                         r['org'] or None, r['object'] or None,
                         (r.get('account') or '').strip() or None, fn, r['name'],
                         r['account_type'], r['level'], fy, fy)
        funds.setdefault(fund, (fund, r['fund_name'],
                                FUND_KIND.get(fund, (None, None, None))[1],
                                FUND_KIND.get(fund, (None, None, None))[2]))
        facts.append((aid, fy, int(r['period']), num(r['original']), num(r['transfers']),
                      num(r['revised']), num(r['expended']), num(r['encumbered']),
                      num(r['available']), num(r['pct_used']),
                      r['rounded_columns'], r['doc_id']))
    for code, (name, kind, restr) in FUND_KIND.items():
        funds.setdefault(code, (code, name, kind, restr))
    db.executemany('INSERT OR REPLACE INTO fund VALUES (?,?,?,?)', list(funds.values()))
    db.executemany('INSERT OR REPLACE INTO account VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   list(accounts.values()))
    db.executemany('INSERT OR REPLACE INTO ledger_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                   facts)
    return len(accounts)


def load_funds(db):
    """Fund balance activity, and grants as the budget documents list them."""
    act, seen_funds = [], {}
    for r in rows('school-special-revenue-fy26-q3'):
        fund = (r['fund'] or '').lstrip("'")     # an Excel text-prefix apostrophe survives
        if not fund:
            continue
        # The fund's NAME lives only in this report. Without it the request document
        # lists bare codes, which is not something anybody can act on.
        seen_funds[fund] = (fund, (r['name'] or '').strip() or None,
                            FUND_KIND.get(fund, (None, None, None))[1],
                            FUND_KIND.get(fund, (None, None, None))[2])
        act.append((fund, 2026, 9, None, num(r['revenue']), num(r['salaries']),
                    num(r['expenditure']), num(r['encumbered']), num(r['balance']),
                    SPECIAL_REV_DOC))
    # Do not overwrite a fund already described from FUND_KIND, which carries the
    # restriction; fill in only what is not there.
    db.executemany('INSERT OR IGNORE INTO fund VALUES (?,?,?,?)', list(seen_funds.values()))
    db.executemany('INSERT OR REPLACE INTO fund_activity VALUES (?,?,?,?,?,?,?,?,?,?)', act)

    dese = []
    for r in rows('dese-radar'):
        dese.append((r['lea'], r['district'], int(r['fy']), r['group'], r['measure'],
                     num(r['value']), r['reconciles'], r['doc_id']))
    db.executemany('INSERT OR REPLACE INTO dese_measure VALUES (?,?,?,?,?,?,?,?)', dese)

    stated = []
    for r in rows('stated-figures'):
        stated.append((int(r['fy']), r['metric'], num(r['amount']), r['stated_on'],
                       r['stated_by'], r['basis'], r['doc_id'], r['source_ref'],
                       r['quote'], num(r['supersedes']), r['note']))
    db.executemany('INSERT OR REPLACE INTO stated_figure VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   stated)

    grants = []
    for r in rows('grants-history'):
        grants.append((r['fy'], r['kind'], r['name'], num(r['amount']), r['owner'],
                       1 if r.get('disagreement') else 0, r.get('doc'),
                       r.get('source_url'), r.get('sha256')))
    db.executemany('INSERT OR REPLACE INTO grant_award VALUES (?,?,?,?,?,?,?,?,?)', grants)
    return len(act), len(grants), len(stated), len(dese)


DESE_FUNCTION_DOC = 'sources/state-dese/district-expenditures-by-function.xlsx'


def load_dese_function(db):
    """DESE's function-code split of general fund against grants and revolving money.

    Both CSVs are written by `extract_dese_finance.py`, which refuses to write unless the
    hierarchy it asserts still holds in all 5,479 district-years and unless its two
    cross-checks against the RADAR workbook match SOMETHING -- a join that matches nothing
    looks exactly like data that is absent.

    This loader adds the assertion the extract cannot make: that `level` survived the
    load. A NULL or unknown level here would let a caller sum a rollup with its own
    detail, which is the one failure mode this pair of tables exists to prevent.
    """
    fn = []
    for r in rows('dese-function-expenditure'):
        fn.append((int(r['fy']), r['lea'], r['district'], r['level'], r['func_cat_code'],
                   r['func_cat_desc'], r['func_code'], r['func_desc'], r['in_out_dist'],
                   num(r['gen_fund']), num(r['grants_revolving']), num(r['total']),
                   num(r['per_pupil']), r['reconciles'], r['doc_id']))
    db.executemany('INSERT OR REPLACE INTO dese_function_expenditure '
                   'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', fn)
    sw = []
    for r in rows('dese-function-statewide'):
        sw.append((int(r['fy']), r['level'], r['func_cat_code'], r['func_code'],
                   r['func_desc'], int(r['districts']), num(r['gen_fund_total']),
                   num(r['grants_revolving_total']), num(r['total']), num(r['grant_share']),
                   r['per_pupil_basis'], num(r['per_pupil_min']), num(r['per_pupil_p25']),
                   num(r['per_pupil_median']), num(r['per_pupil_p75']),
                   num(r['per_pupil_max']), num(r['lunenburg_per_pupil']),
                   r['lunenburg_rank_of_districts'], r['doc_id']))
    db.executemany('INSERT OR REPLACE INTO dese_function_statewide '
                   'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', sw)

    LEVELS = {'total', 'rollup', 'category', 'detail'}
    for table in ('dese_function_expenditure', 'dese_function_statewide'):
        got = {r[0] for r in db.execute('SELECT DISTINCT level FROM "%s"' % table)}
        if got != LEVELS:
            raise SystemExit(
                '%s carries levels %s, expected %s.\n'
                'The level column is what stops a rollup being summed with its own '
                'detail. A build\nthat has lost it would produce a plausible total '
                'four times too large.' % (table, sorted(got), sorted(LEVELS)))
    return len(fn), len(sw)


# The fourteen DESE datasets ingested on 8 September 2026, as (csv name, table, the
# level column that must survive the load, the levels that column is allowed to hold).
#
# The level column is the whole defence. Every one of these sources puts summary rows in
# the same column space as detail and names neither, so a build that lost the level would
# let a caller sum a rollup with the detail beneath it and get a plausible number several
# times too large -- which is precisely what happened once with the function-code
# expenditures ($116M for a $26.6M district).
DESE_DATASETS = [
    ('dese-teacher-program-area', 'dese_teacher_program_area', 'org_level',
     {'state', 'district', 'school'}),
    ('dese-teacher-subject', 'dese_teacher_subject', 'subject_level',
     {'all', 'group', 'subject'}),
    ('dese-teacher-grade-subject', 'dese_teacher_grade_subject', 'subject_level',
     {'all', 'group', 'subject'}),
    ('dese-educator-workforce', 'dese_educator_workforce', 'race_level',
     {'all', 'detail'}),
    ('dese-enrollment', 'dese_enrollment', 'org_level',
     {'state', 'district', 'school', 'collaborative'}),
    ('dese-sped-indicator', 'dese_sped_indicator', 'student_group_level',
     {'all', 'detail'}),
    ('dese-sped-program', 'dese_sped_program', 'indicator_level', {'total', 'member'}),
    ('dese-sped-trajectory', 'dese_sped_trajectory', 'geo_level', {'state', 'district'}),
    ('dese-sped-movement', 'dese_sped_movement', 'grades_level', {'all', 'grade'}),
    ('dese-town-enrollment', 'dese_town_enrollment', None, None),
    ('dese-ch70-formula', 'dese_ch70_formula', 'level', {'state', 'district'}),
    ('dese-ch70-aid-factor', 'dese_ch70_aid_factor', 'level', {'state', 'district'}),
    ('dese-ch70-contribution', 'dese_ch70_contribution', None, None),
    ('dese-circuit-breaker', 'dese_circuit_breaker', 'level', {'state', 'district'}),
    ('dese-ch70-statewide', 'dese_ch70_statewide', None, None),
    # `org_type` is the level column here, and it is the ONE thing standing
    # between a caller and summing a district with its own schools.
    ('dese-class-size', 'dese_class_size', 'org_type', {'District', 'School'}),
]

# Which columns are text in these tables. Everything else that is not `fy` is a figure,
# and `num()` turns a blank into NULL rather than into nought -- DESE suppresses small
# cells, and a suppressed count read as zero understates every total it enters.
DESE_TEXT_COLS = {
    'lea', 'district', 'org_code', 'org_name', 'org_level', 'subject', 'subject_level',
    'race_ethnicity', 'race_level', 'job_class', 'geo_level', 'grades', 'grades_level',
    'student_group', 'student_group_level', 'indicator_category', 'indicator',
    'indicator_level', 'grade_span', 'placement_at_start', 'value_type', 'comments',
    'reconciles', 'agrees_with_teacher_subject', 'repeats_prior_year', 'doc_id',
    'town', 'enrollment_reason', 'doc_id_sending', 'doc_id_receiving', 'org4_code',
    'lea_number', 'level', 'municipality', 'nss_stage', 'student_teacher_ratio_printed',
    'measure', 'basis', 'lunenburg_rank_of_districts',
    'kind', 'org_type', 'subj',
}
# `printing` is an ordinal, not a figure: 1 for the first row published under a natural
# key, 2 for the next. It is part of the primary key of three tables.
# `sy` is the school year ending, and it is an integer for the same reason `fy` is:
# `dese_class_size` keeps the publisher's own column name (see its schema note).
DESE_INT_COLS = {'fy', 'sy', 'printing', 'districts'}


def load_dese_datasets(db):
    """The fourteen DESE staffing, student and Chapter 70 tables.

    Each CSV is written by one of `extract_dese_staffing.py`, `extract_dese_students.py`
    or `extract_dese_state_aid.py`, every one of which refuses to write unless the
    identities its source states about itself still hold and unless its cross-checks match
    SOMETHING. This loader adds the two assertions those extracts cannot make:

      1. the LEVEL column survived the load, and holds exactly the values it should;
      2. nothing loaded empty. An empty table passes every downstream check and renders a
         blank page -- which is what `build_insurance_charts.py` did until it was caught.
    """
    total = 0
    for name, table, level_col, levels in DESE_DATASETS:
        data = rows(name)
        if not data:
            raise SystemExit(
                '%s.csv is empty, so %s would load as an empty table.\n'
                'An empty table passes every check downstream and renders a blank page.\n'
                'Re-run the extract that writes it.' % (name, table))
        cols = list(data[0].keys())
        placeholders = ','.join('?' * len(cols))
        batch = []
        for r in data:
            batch.append(tuple(
                r[c] if c in DESE_TEXT_COLS else
                (int(r[c]) if c in DESE_INT_COLS else num(r[c])) for c in cols))
        db.executemany('INSERT OR REPLACE INTO %s (%s) VALUES (%s)'
                       % (table, ','.join('"%s"' % c for c in cols), placeholders), batch)
        n = db.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]
        if n != len(data):
            raise SystemExit(
                '%s holds %d rows from a %d-row CSV.\n'
                'INSERT OR REPLACE dropped %d row(s) to a primary key collision, and a\n'
                'load that drops rows looks exactly like data that was never published.\n'
                'Either the key is too narrow for what DESE published, or a `printing`\n'
                'column is needed -- see the schema note. Nothing here may be lost '
                'quietly.' % (table, n, len(data), len(data) - n))
        if level_col:
            got = {x[0] for x in db.execute(
                'SELECT DISTINCT "%s" FROM "%s"' % (level_col, table))}
            if not got <= levels or not got:
                raise SystemExit(
                    '%s.%s carries %s; only %s are known.\n'
                    'The level column is what stops a rollup being summed with its own '
                    'detail. A\nbuild that has lost it would produce a plausible total '
                    'several times too large.'
                    % (table, level_col, sorted(got), sorted(levels)))
        total += n
    return total


def load_budget_figures(db):
    """line-history.csv: every line every document prints, with the stage it printed.

    `source` is a BARE FILENAME while `document.doc_id` is a repository path, so the
    largest fact table in this database -- 8,598 figures, most of what the site quotes --
    pointed at documents by a name that resolved to none of them. Every row had a doc_id
    and not one of the twenty distinct values joined. Nothing caught it because the only
    check ever run was `doc_id IS NOT NULL`, which is a fact about a string rather than
    about a document, and because `v_provenance` LEFT JOINs, so a total miss renders as
    blank columns instead of an error.

    Resolved by `resolve_budget_documents()` AFTER the document table is written -- it is
    not written until `finish_documents`, so doing it here silently matched nothing and
    dropped all 8,598 rows. The loader stores the filename; the post-pass rewrites it.

    AND THE STAGE ALLOWLIST BELOW SILENTLY DROPPED 3,316 ROWS during the 7 September 2026
    rename of `actual` to `restated`. The CSV was rewritten, the CHECK constraint was
    updated, `check_no_stage_actual` reported success -- and the rows were gone, because
    this filter still named the old value and a row that fails it is SKIPPED, not refused.

    Every signal pointed the right way. The guard said "none of them calls it `actual`",
    which was true and meaningless: they were not there to call it anything. An absent row
    and a correctly-renamed row look identical to a check that only asks whether the OLD
    name is present.

    One thing caught it: `build_variance_charts` refused to write because its pivot matched
    nothing. A generator that fails closed is worth more than three that report success,
    and this is the case that proves it. The count assertion at the end of this function
    exists so the next rename does not need luck.
    """
    STAGES = ('proposed', 'settled', 'restated')
    out, lines, skipped = [], {}, {}
    for r in rows('line-history'):
        fy, value = r['fy'], num(r['value'])
        if not fy.isdigit() or value is None:
            continue
        if r['stage'] not in STAGES:
            skipped[r['stage']] = skipped.get(r['stage'], 0) + 1
            continue
        out.append((r['key'], r['label'], int(fy), r['stage'], r.get('variant', ''),
                    value, int(r['documents_disagree'] or 0), r['source']))
        lines.setdefault(r['key'], r['label'])

    # A STAGE THIS LOADER DOES NOT RECOGNISE IS A DEFECT, NOT A ROW TO SKIP.
    #
    # This filter dropped 3,316 rows during the rename of `actual` to `restated` and
    # reported nothing, because an unknown value fell through `continue`. The CSV is the
    # source of truth here; if it holds a stage the database has never heard of, the right
    # answer is to stop and be told, not to quietly publish a smaller database.
    if skipped:
        raise SystemExit(
            'line-history.csv holds %d row(s) whose stage this loader does not recognise: '
            '%s.\n  Known stages: %s.\n  A row with an unknown stage is DROPPED, and a '
            'dropped row is invisible — this is exactly how the `actual` -> `restated` '
            'rename lost 3,316 figures while every check reported success. Add the stage '
            'here and to the CHECK constraint on budget_figure, or fix the extractor.'
            % (sum(skipped.values()),
               ', '.join('%r (%d)' % (k, v) for k, v in sorted(skipped.items())),
               ', '.join(repr(s) for s in STAGES)))

    # And the stages that SHOULD be here must actually be here. The check above catches a
    # renamed stage; this catches one that vanished from the extractor entirely, which
    # looks identical downstream and produces no unknown value to trip over.
    present = {r[3] for r in out}
    missing = [s for s in STAGES if s not in present]
    if missing:
        raise SystemExit(
            'line-history.csv produced no rows at all for stage(s): %s.\n  Every one of '
            '%s is expected. A stage that silently empties looks exactly like data that '
            'was never collected.' % (', '.join(missing), ', '.join(STAGES)))
    db.executemany('INSERT OR REPLACE INTO budget_figure VALUES (?,?,?,?,?,?,?,?)', out)
    db.executemany('INSERT OR IGNORE INTO budget_line VALUES (?,?,?,?,?)',
                   [(k, v, None, None, None) for k, v in lines.items()])
    return len(out)


def load_workbook(db):
    """lps-budget-lines.csv unpivoted. The worksheet row travels with every figure so a
    cell stays quotable: row 401 column F is `Salary Reserve`, $347,338.

    The sheet's own TOTAL rows are loaded too, marked `row_kind='total'`, so the line
    sum can be reconciled to the total the source itself prints rather than to our sum
    of it. Every query over lines must filter `row_kind='line'` or it double-counts."""
    out, lines = [], {}
    for r in rows('lps-budget-lines'):
        label = r.get('line_item')
        if not label or not (r.get('row') or '').isdigit():
            continue
        row_kind = 'total' if r.get('kind') == 'total' else 'line'
        k = key(label)
        if row_kind == 'line':
            lines[k] = (k, label, r.get('section'), r.get('function_group'),
                        r.get('kind'))
        for col, (fy, kind) in WORKBOOK_COLUMNS.items():
            v = num(r.get(col))
            if v is not None:
                out.append((int(r['row']), k, fy, kind, v, row_kind, WORKBOOK_DOC))
    db.executemany('INSERT OR REPLACE INTO budget_line VALUES (?,?,?,?,?)',
                   list(lines.values()))
    db.executemany('INSERT OR REPLACE INTO workbook_figure VALUES (?,?,?,?,?,?,?)', out)
    return len(out)


# `fy` IS THE EXCEPTION TO "EVERYTHING TEXT", AND THIS IS WHY.
#
# The generic loaders below deliberately declare every column TEXT so that nothing is
# silently changed on the way in. That is right for values. It was WRONG for `fy`, and it
# cost us a whole class of silent zero.
#
# SQLite does not compare a TEXT '2023' equal to an INTEGER 2023. It does not raise
# either -- it returns no rows. So `WHERE fy = 2023` answered correctly against
# `budget_figure` (INTEGER, declared in DDL above) and returned NOTHING against
# `revenue_history`, `annual_report_receipts` and 42 other tables, with no error to read.
# Eighteen tables said yes and forty-four said nothing, to the same query.
#
# That is the third sub-cause in CLAUDE.md -- a result that matches nothing looks exactly
# like data that is absent -- appearing in the one column every table is filtered on.
#
# So `fy` is coerced to INTEGER **only when every value in the column is a bare four-digit
# year**, which changes no fact: '2014' and 2014 are the same year. Where a value is not a
# year the column stays TEXT, because those are not years and must not be forced into one:
#
#   grant_award.fy / grants_history.fy = 'FY21-24'  a genuinely multi-year ESSER award
#   rate_register.fy                   = ''         a rate with no year set
#
# `check_fy_types` below refuses to write the database if a new table arrives with a TEXT
# `fy` that is not on that list, so the next one fails the build instead of the query.
FY_TEXT_EXPECTED = {
    'grant_award': "the ESSER award spans FY21-24 and is not a single year",
    'grants_history': "the ESSER award spans FY21-24 and is not a single year",
    'rate_register': "one rate carries no fiscal year at all",
}


def fy_is_year(data, col='fy'):
    """True when every value in `col` is a bare four-digit year, so INTEGER loses nothing."""
    vals = [r.get(col) for r in data]
    return bool(vals) and all(v is not None and str(v).strip().isdigit()
                              and len(str(v).strip()) == 4 for v in vals)


def coerce_fy(data, cols):
    """Return (declared types per column, a row-reader) with `fy` typed as a year if it is.

    Returns TEXT for everything else -- see the note above for why that is deliberate.
    """
    as_year = 'fy' in cols and fy_is_year(data)
    types = ['INTEGER' if (c == 'fy' and as_year) else 'TEXT' for c in cols]

    def read(r):
        return [int(str(r[c]).strip()) if (c == 'fy' and as_year) else r[c] for c in cols]
    return types, read


def check_fy_types(db):
    """Refuse to write if any table's `fy` is TEXT for a reason nobody wrote down.

    A silent zero is the worst failure this database has, because it is indistinguishable
    from an honest empty answer. This is the check that makes the next one loud.
    """
    bad = []
    for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = {d[1]: d[2] for d in db.execute('PRAGMA table_info("%s")' % t)}
        if cols.get('fy') != 'TEXT' or t in FY_TEXT_EXPECTED:
            continue
        vals = [r[0] for r in db.execute('SELECT DISTINCT fy FROM "%s"' % t)]
        if vals and all(v is not None and str(v).strip().isdigit()
                        and len(str(v).strip()) == 4 for v in vals):
            bad.append(t)
    if bad:
        raise SystemExit(
            'fy stored as TEXT but holding only years, in: %s\n'
            '  `WHERE fy = 2023` returns ZERO ROWS against these and raises nothing.\n'
            '  Load them through coerce_fy(), or add them to FY_TEXT_EXPECTED with a '
            'reason.' % ', '.join(bad))
    return len(FY_TEXT_EXPECTED)


def load_reference(db):
    """Load the remaining CSVs verbatim, one table each, all columns TEXT.

    These are reference data, not the analytical spine. Loading them verbatim means the
    table is exactly the published CSV -- no coercion, so nothing can be silently changed
    on the way in -- and a query that needs a number casts it explicitly.
    """
    n = 0
    for name in REFERENCE:
        data = rows(name)
        if not data:
            continue
        table = name.replace('-', '_')
        cols = list(data[0].keys())
        # A CSV may repeat a header (total-salaries-history has two `total` columns);
        # keep the first and suffix the rest so the table still round-trips.
        seen, safe = {}, []
        for c in cols:
            c2 = c or 'col'
            if c2 in seen:
                seen[c2] += 1
                c2 = '%s_%d' % (c2, seen[c2])
            else:
                seen[c2] = 0
            safe.append('"%s"' % c2)
        types, read = coerce_fy(data, cols)
        db.execute('CREATE TABLE "%s" (%s)'
                   % (table, ', '.join('%s %s' % (c, t) for c, t in zip(safe, types))))
        db.executemany('INSERT INTO "%s" VALUES (%s)' % (table, ','.join('?' * len(cols))),
                       [read(r) for r in data])
        n += len(data)
    return n


# Datasets that were on disk as CSVs and not in the database, so nothing could query
# them. Split deliberately: the first list is ANALYSIS DATA and belongs in the read model;
# the second is archive PLUMBING — what has been copied where, which links still resolve —
# and belongs in the manifests rather than in a database somebody is asking budget
# questions of.
UNLOADED = [
    ('line-history', 'Every budget line, every year, as extracted'),
    ('dese-radar', 'DESE all-funds per-pupil figures, all districts'),
    ('munis-ledger', 'The MUNIS chart of accounts as delivered'),
    ('staff-position-map', 'Printed roster titles mapped to positions'),
    ('lps-budget-lines', 'The district budget book’s own line list'),
    ('account-names', 'What each abbreviated account name expands to'),
    ('grants-history', 'Grants by year'),
    ('town-ledger-fy26-q3', 'The FY26 Q3 town ledger, by department'),
    ('school-special-revenue-fy26-q3', 'The FY26 Q3 school special revenue funds'),
    ('line-history-coverage', 'Which lines have how many years of history'),
    # The semantics, as DATA. A description that lives only in a docstring is invisible to
    # every caller that is not reading the source -- including /api/query, which is how an
    # agent meets this database. Loading them means "what does this column mean" is
    # answerable in SQL, by the same route as every other question here.
    ('balance-sheet', 'The combined balance sheet READ from the page — what the town '
     'HOLDS, against the flow tables everything else here measures'),
    ('balance-sheet-printed-totals', 'The totals each balance sheet prints, quoted'),
    # The ENTERPRISE-FUNDS combining balance sheet, FY2024-FY2025. A SEPARATE dataset,
    # deliberately: it is four named ratepayer funds (Sewer, Water, Solid Waste, PEG
    # Access) with a memorandum-only total column, not the six fund-type columns of the
    # town-wide sheet above, and FY2024 and FY2025 print no town-wide sheet at all.
    # Appending it to `balance_sheet` would put rows into a schema whose column meanings
    # they do not share. FY2024 prints the SAME sheet twice, so `printing` (1 or 2) must
    # be collapsed on before anything is summed.
    ('enterprise-balance-sheet', 'The enterprise-funds combining balance sheet READ from '
     'the page — what the four RATEPAYER funds hold; not general-fund money'),
    ('enterprise-balance-sheet-printed-totals',
     'The totals and the printed Proof row each enterprise balance sheet states, quoted'),
    # PEG Access / Public Access Cable, FY2015-FY2025, read from the page. Kept apart from
    # `enterprise_balance_sheet` on purpose: that table is a STOCK at 30 June and this is a
    # FLOW across the year, and for FY2025 -- the one year both cover -- they do not
    # reconcile. Nothing here is a tax dollar; it is the Comcast franchise fee.
    ('peg-access', 'Every PEG Access expense line READ from the page, with the percentage '
     'of total expense the report prints beside it'),
    ('peg-access-printed-totals',
     'The revenue-versus-expenses statement each report prints, row by row, quoted'),
    ('peg-access-identities',
     'The arithmetic each PEG statement states about itself, over the printed ordinals'),
    ('special-revenue-read', 'The special revenue schedule READ from the page — the '
     'only version of it that ties to its own printed total'),
    ('special-revenue-printed-totals', 'The GRAND TOTAL each report prints, quoted'),
    ('table-semantics', 'What each table is: its role, its grain, what it answers'),
    ('column-glossary', 'What each column name means, and what goes wrong if ignored'),
]
PLUMBING = ('archive-manifest', 'archive-push-state', 'copy-status', 'link-status',
            'document-basis', 'stated-figures', 'dataset-provenance')


def load_unloaded(db):
    """CSVs that existed on disk and could not be queried.

    Fifteen datasets were sitting in `sources/data` and in no table, so `/api/query` could
    not reach them and no worked example could use them. Ten are analysis data and load
    here; the rest is archive bookkeeping — what has been copied where, which links still
    resolve — which belongs in a manifest rather than in a database somebody is asking
    budget questions of. That split is a judgement and is recorded in `PLUMBING` above so
    it can be argued with.
    """
    n = 0
    for name, _ in UNLOADED:
        data = rows(name)
        if not data:
            continue
        table = name.replace('-', '_')
        cols = list(data[0].keys())
        types, read = coerce_fy(data, cols)
        db.execute('CREATE TABLE %s (%s)'
                   % (table, ', '.join('"%s" %s' % (c, t) for c, t in zip(cols, types))))
        db.executemany('INSERT INTO %s VALUES (%s)' % (table, ','.join('?' * len(cols))),
                       [read(r) for r in data])
        n += len(data)
    return n


def load_money_model(db):
    """The classification of every revenue account, fund and department — as DATA.

    Everything this project learned about how Lunenburg's money is organised lived in
    Python dictionaries inside four generator scripts, two of them holding their own copy
    of the revenue classification. That is a derived thing written down, in a place nothing
    checks, in four copies — and it meant none of it was queryable. A caller could ask the
    database what the town SPENT and not what any of it MEANS, which is the more useful
    question and the one this project exists to answer.

    So the CSVs are the source of truth and this loads them. Four tables and two views:

      money_classification   one row per revenue account, fund, department or grant code
      money_edges            which source pays which use, and whether traced or presumed
      money_assumptions      every assumption still load-bearing, and what would settle it
      money_gaps             what the records cannot answer, and the document that would
      v_revenue_classified   revenue by fiscal year and class — "what comes in, how much"
      v_spending_classified  spending by fiscal year and class — the same, going out

    `how` is the column that matters: `stated` means the town's own name says it,
    `neighbours` means it was read from what an account sits among, and `outside` means it
    depends on knowledge from beyond this archive and is the weakest kind here.
    """
    n = 0
    for name, table, index in (
            ('money-classification', 'money_classification', '(kind, "key")'),
            ('money-edges', 'money_edges', '(source)'),
            ('money-assumptions', 'money_assumptions', None),
            ('money-gaps', 'money_gaps', '(side)')):
        data = rows(name)
        if not data:
            continue
        cols = list(data[0].keys())
        types, read = coerce_fy(data, cols)
        db.execute('CREATE TABLE %s (%s)'
                   % (table, ', '.join('"%s" %s' % (c, t) for c, t in zip(cols, types))))
        db.executemany('INSERT INTO %s VALUES (%s)' % (table, ','.join('?' * len(cols))),
                       [read(r) for r in data])
        if index:
            db.execute('CREATE INDEX ix_%s ON %s%s' % (table, table, index))
        n += len(data)
    if not n:
        return 0

    # WHAT COMES IN, BY CLASS AND YEAR. An account with no classification row appears as
    # `unclassified` rather than vanishing — a join that drops rows looks exactly like data
    # that is absent, and 113 of the 192 accounts carry nothing anyway.
    db.execute("""
        CREATE VIEW v_revenue_classified AS
        SELECT r.fy, r.period, r.fund, r.name AS account,
               COALESCE(m."group", 'local') AS class,
               COALESCE(m.label, 'Local receipts') AS class_label,
               r.budgeted, r.received
        FROM v_revenue r
        LEFT JOIN money_classification m
               ON m.kind = 'revenue_account' AND m."key" = r.name AND m."group" <> ''""")

    # REVENUE OVER TIME, from the annual reports. Five years, and ONLY five — the other
    # eight have no checked rows and are excluded rather than shown as zero.
    #
    # A TABLE, not a view, and the reason matters: the join key is the source name with
    # every space and punctuation mark removed, which needs a function SQLite has to be
    # given. A view calling a custom function works only in the connection that created it
    # — it fails from any other client and from D1, which has no custom functions at all.
    # So the key is computed here, once, and stored.
    #
    # The squashing is not cosmetic. OCR splits words in some editions: `REAL EST AT E T
    # AXES` and `REAL ESTATE TAXES` are the same line, and **73 of the 197 printed names
    # were split this way**. Grouping on the raw name shows Real Estate Taxes as a
    # four-year series and a one-year series instead of one five-year series.
    import re as _re
    cls = {r[0]: (r[1], r[2]) for r in db.execute(
        'SELECT "key", "group", label FROM money_classification WHERE kind=?',
        ('report_receipt',))}
    src = db.execute("""SELECT fy, source, amount, document, page
                        FROM annual_report_receipts WHERE status='checked'""").fetchall()
    db.execute('CREATE TABLE revenue_history (fy INTEGER, printed_name TEXT, '
               'source_key TEXT, class TEXT, label TEXT, amount REAL, '
               'document TEXT, page TEXT)')
    hist = []
    for fy, source, amount, document, page in src:
        k = _re.sub(r'[^A-Z0-9]', '', (source or '').upper())
        g, lab = cls.get(k, ('local', source))
        hist.append((int(fy), source, k, g, lab, float(amount or 0), document, page))
    db.executemany('INSERT INTO revenue_history VALUES (?,?,?,?,?,?,?,?)', hist)
    db.execute('CREATE INDEX ix_revenue_history ON revenue_history(fy, class)')
    unmatched = sum(1 for h in hist if h[2] not in cls)
    if unmatched:
        raise SystemExit(f'revenue_history: {unmatched} rows matched no classification. '
                         f'A join that matches nothing looks exactly like data that is '
                         f'absent — refusing to write it.')

    # AND WHAT GOES OUT. Departments carry the `who decides` class; anything unclassified
    # is `discretionary`, which is a residual and is labelled as one everywhere else too.
    db.execute("""
        CREATE VIEW v_spending_classified AS
        SELECT l.fy, l.period, a.dept, a.name AS department,
               COALESCE(m.classification, 'discretionary') AS control,
               COALESCE(m.how, 'residual') AS control_how,
               l.original AS voted, l.revised, l.expended
        FROM ledger_snapshot l
        JOIN account a USING (account_id)
        LEFT JOIN money_classification m
               ON m.kind = 'department' AND m."key" = a.dept
        WHERE a.level = 'department' AND a.account_type = 'expense'""")
    return n


def load_role_classification(db):
    """What kind of job each printed roster title is, and a view that joins it to the rows.

    The town's name for the same job changed five times in fifteen years -- Tutor, Aide,
    Tutors/Aides, Paraprofessional, Para, (para), Sped Para -- so a filter on the printed
    title measures the house style rather than the staffing. `role-classification.csv` is
    a dictionary over the 1,030 distinct (title, heading) pairs; this loads it and defines
    `v_staff_roster`, which is the table an analysis should actually use.

    `role_category` is OUR inference and `role_raw` is what the town printed. The view
    carries both, and `classified_by` names the rule, because a classification without its
    evidence beside it is how the old `position` column came to report 0 kindergarten
    paraprofessionals in a year that had five.
    """
    data = rows('role-classification')
    if not data:
        return 0
    cols = list(data[0].keys())
    db.execute('CREATE TABLE role_classification (%s)'
               % ', '.join('"%s" TEXT' % c for c in cols))
    db.executemany('INSERT INTO role_classification VALUES (%s)'
                   % ','.join('?' * len(cols)),
                   [[r[c] for c in cols] for r in data])
    db.execute('CREATE INDEX ix_role_classification '
               'ON role_classification(role_raw, grade_or_dept)')
    db.execute("""
        CREATE VIEW v_staff_roster AS
        SELECT e.fy, e.school, e.page, e.name,
               e.role_raw, e.grade_or_dept, e.position AS position_legacy,
               c.role_category, c.role_grade, c.classified_by,
               e.document
        FROM staff_roster_entries e
        LEFT JOIN role_classification c
               ON c.role_raw = e.role_raw AND c.grade_or_dept = e.grade_or_dept
    """)
    return len(data)


def check_document_paths(db):
    """No document row may name a file that is not on disk.

    43 of 600 did. Every one was a casualty of the town split -- a document that moved to
    `town-supplementary/` or `town-annual-reports/` while `document-basis.csv` went on
    naming its old home -- and the rows sat in the database being cited as the place to
    check a figure. `/api/query` would have handed those addresses to callers as
    provenance.

    An address that 404s is worse than no address, because it looks like provenance and
    fails only for the reader who actually tries it. So this refuses to finish the build.
    """
    dead = [(d, p) for d, p in db.execute('SELECT doc_id, path FROM document')
            if p and not os.path.exists(os.path.join(ROOT, p))]
    if dead:
        raise SystemExit(
            f'{len(dead)} document row(s) name a file that is not on disk:\n  '
            + '\n  '.join(p for _, p in dead[:8])
            + (f'\n  ... and {len(dead) - 8} more' if len(dead) > 8 else '')
            + '\n\n  Run `python3 scripts/classify_document_basis.py` and rebuild. A '
              'document row is\n  an address a reader is told to check; one that 404s '
              'looks like provenance and is not.')
    return len(dead)


def load_provenance(db):
    """The join from a row to the document it was read out of.

    Fifteen tables carry a `doc_id`. Thirty-eight do not, and the annual-report extracts
    are the ones that matter: `report_appropriations` has 4,665 rows and no route to a
    document at all. They are loaded verbatim on purpose -- the table is exactly the
    published CSV, so nothing can be silently changed on the way in -- so the answer is
    not to mutate them but to publish the join beside them.

    `build_dataset_provenance.py` already resolves every dataset-edition to its document,
    with the address, the publisher's label and the sha256. This loads that, so a query
    can reach provenance without leaving SQL:

        SELECT r.*, d.document, d.sha256, d.upstream
        FROM report_appropriations r
        JOIN dataset_document d
          ON d.dataset = 'report-appropriations' AND d.edition = r.edition

    Why it matters more here than anywhere else: a figure is only checkable if somebody
    can get back to the document it came from. An API that answers arbitrary questions and
    cannot say where the answer came from is exactly the thing this project is built not
    to be.
    """
    data = rows('dataset-provenance')
    if not data:
        return 0
    cols = list(data[0].keys())
    db.execute('CREATE TABLE dataset_document (%s)'
               % ', '.join('"%s" TEXT' % c for c in cols))
    db.executemany('INSERT INTO dataset_document VALUES (%s)' % ','.join('?' * len(cols)),
                   [[r[c] for c in cols] for r in data])
    db.execute('CREATE INDEX ix_dataset_document ON dataset_document(dataset, edition)')
    # A row with no document is the failure this table exists to prevent, so it is
    # counted rather than assumed away.
    blank = db.execute("SELECT COUNT(*) FROM dataset_document "
                       "WHERE document IS NULL OR document = ''").fetchone()[0]
    if blank:
        raise SystemExit(
            f'dataset_document: {blank} of {len(data)} rows resolve to no document. '
            f'Run scripts/build_dataset_provenance.py, which fails loudly when the join '
            f'breaks.')
    return len(data)


CHECKS = []


def check(db, label, got, want, tol=0.005):
    ok = got is not None and abs(got - want) <= tol
    CHECKS.append((ok, label, got, want))
    print('  %s  %-52s %s' % ('OK  ' if ok else 'FAIL', label,
                              f'{got:,.2f}' if got is not None else 'None'))


def resolve_budget_documents(db):
    """Rewrite budget_figure.doc_id from a bare filename to the document's real id.

    Runs after `finish_documents`, which is the first moment the document table exists.
    Anything still unresolved is reported rather than left pointing nowhere: a figure
    whose address goes to no document is worse than one that admits it has none, because
    only the second kind can be noticed.
    """
    by_base = {}
    for (doc_id,) in db.execute('SELECT doc_id FROM document'):
        by_base.setdefault(os.path.basename(doc_id), doc_id)
    fixed, missing = 0, set()
    for (raw,) in db.execute('SELECT DISTINCT doc_id FROM budget_figure').fetchall():
        if not raw or raw in by_base.values():
            continue
        full = by_base.get(os.path.basename(raw))
        if full:
            db.execute('UPDATE budget_figure SET doc_id = ? WHERE doc_id = ?', (full, raw))
            fixed += 1
        else:
            missing.add(raw)
    db.commit()
    unresolved = db.execute(
        'SELECT COUNT(*) FROM budget_figure b LEFT JOIN document d ON d.doc_id = b.doc_id '
        'WHERE d.doc_id IS NULL').fetchone()[0]
    return fixed, sorted(missing), unresolved


def check_join_key(db):
    """The function code must survive the load, and must still meet the budget.

    It did not survive, for as long as this database has existed. `munis-ledger.csv`
    carried a `function` column and `account` had no column to put it in, so the one join
    between the district's budget and the town's books was discarded on every build --
    silently, because nothing compared the loader's output to its input. An analysis run
    against the database concluded the two sides shared no key at all, which was true of
    the database and false of the data.

    Two assertions, both cheap:
      1. Some rows carry a function code. Zero means the column was dropped again.
      2. Those codes still overlap the budget's. A drift to zero means one side recoded.
    """
    coded = db.execute('SELECT COUNT(*) FROM account WHERE function IS NOT NULL').fetchone()[0]
    if not coded:
        raise SystemExit(
            'account.function is empty. The join between the budget and the ledger is '
            'gone. Check that munis-ledger.csv still has a `function` column and that '
            'load_munis still carries it.')
    overlap = db.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT function AS c FROM account WHERE function IS NOT NULL
            INTERSECT
            SELECT DISTINCT substr(function_group, 1, 4) FROM budget_line
             WHERE function_group IS NOT NULL AND function_group != '')""").fetchone()[0]
    if overlap < 20:
        raise SystemExit(
            f'only {overlap} function codes are shared between account and budget_line. '
            'They were 41. One side has been recoded and the join no longer holds.')
    return coded, overlap


def check_no_stage_actual(db):
    """No table may carry a stage called `actual`, because none of them holds one.

    Every figure loaded under that stage comes from a district BUDGET book, not from the
    accounting system: `document-basis.csv` classifies all sixteen source documents as
    `restatement` (14) or `forward` (2), and none as `ledger`. The stage is now `restated`.

    THE OLD NAME CAUSED THE ERROR IT WAS NAMED FOR. An assessment written on 7 September
    2026 read `stage='actual'` as the ledger and told TJ that twelve years of school
    actuals were available. They are not: the ledger reaches school spending for FY2026
    period 12 and one quarter of FY23, and nowhere else. Rule 13 lists this exact mistake
    in its own table -- "the actuals sheet" against "a forward budget workbook with a
    column headed ACTUALS" -- and it was made anyway, by someone who had just quoted the
    rule.

    A comment cannot prevent that. A name can, and a check keeps the name.
    """
    bad = []
    for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = {d[1] for d in db.execute('PRAGMA table_info("%s")' % t)}
        if 'stage' not in cols:
            continue
        n = db.execute('SELECT COUNT(*) FROM "%s" WHERE stage = ?' % t, ('actual',)).fetchone()[0]
        if n:
            bad.append('  %s: %d row(s)' % (t, n))
    if bad:
        raise SystemExit(
            'a table carries stage=\'actual\', which no figure in this database is:\n'
            + '\n'.join(bad)
            + '\nThese are RESTATEMENTS -- a closed year re-presented inside the budget '
              'book of the party that spent it. The stage is `restated`. If a genuine '
              'ledger series is being loaded, give it its own stage name and say which '
              'ledger document it came from.')
    return sum(1 for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
               if 'stage' in {d[1] for d in db.execute('PRAGMA table_info("%s")' % t)})


def check_stored_queries(db):
    """Every query this database PUBLISHES must actually run against it.

    `table-semantics.csv` carries a `default_query` per table. They are published on the
    schema page and handed to assistants as the worked example for each table, and until
    this ran, NOT ONE OF THEM HAD EVER BEEN EXECUTED. One was dead:

        SELECT fy, section, line, fund_column, amount FROM balance_sheet ...

    There is no `fund_column`; the column is `fund`. A reader who copied the example this
    project gave them got `Error: no such column: fund_column`, on the one surface built
    to make the data easy to reach.

    THE SHAPE IS THE FAMILIAR ONE POINTED A NEW WAY. A column NAME was typed into prose
    and the thing it named moved -- rule 2, except the prose is SQL, so it looks like code
    and gets the credibility of code while having none of the checking. `check_generated`
    cannot catch it because nothing regenerates the file.

    The cure is the one `build_question_bank.py` already applies to the question bank: run
    every stored query on each build, and fail if one stops answering. A query is only
    known to work at the moment it is executed.
    """
    import csv as _csv
    bad = []
    path = os.path.join(DATA, 'table-semantics.csv')
    for r in _csv.DictReader(open(path, encoding='utf-8')):
        q = (r.get('default_query') or '').strip()
        if not q:
            continue
        try:
            db.execute(q).fetchmany(1)
        except Exception as e:                      # noqa: BLE001 -- the message IS the finding
            bad.append('  %s: %s' % (r['table_name'], e))
    if bad:
        raise SystemExit(
            'table-semantics.csv publishes %d query/queries that do not run against this '
            'database:\n%s\nThese are the worked examples the schema page hands a reader. '
            'A published query that errors is worse than none.' % (len(bad), '\n'.join(bad)))
    return sum(1 for r in _csv.DictReader(open(path, encoding='utf-8'))
               if (r.get('default_query') or '').strip())


def reconcile(db):
    """Assert against figures established outside this script, not against itself."""
    print('\nReconciliations')
    q = lambda s: db.execute(s).fetchone()[0]

    # The town ledger, against the report's own printed GRAND TOTAL. The appropriation
    # columns are rounded per row, so the tolerance is one dollar per row (67) -- the
    # same rule extract_town_ledger.py applies, for the same reason.
    check(db, 'town ledger, expended, FY26 P9',
          q("""SELECT SUM(expended) FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=9 AND fund='0100'
                 AND account_type='expense' AND level='department'"""),
          34219013.80)
    check(db, 'town ledger, encumbered, FY26 P9',
          q("""SELECT SUM(encumbered) FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=9 AND fund='0100'
                 AND account_type='expense' AND level='department'"""),
          2626115.87)
    check(db, 'town ledger, original approp, FY26 P9 (67 rounded rows)',
          q("""SELECT SUM(original) FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=9 AND fund='0100'
                 AND account_type='expense' AND level='department'"""),
          51189965.0, tol=67.0)

    # The school department, the row the whole FY25/FY26 surplus question turns on.
    check(db, 'school dept revised budget, FY26 P9',
          q("SELECT revised FROM ledger_snapshot WHERE account_id='0100-300' AND period=9"),
          26323868.0)

    # The revenue side, against its own report's printed TOTAL REVENUES. Stored negative,
    # as MUNIS prints it, so the assertion is negative too -- flipping the sign on the way
    # in would have hidden that the convention exists.
    check(db, 'general fund revenue budgeted, FY26 P9 (192 accounts)',
          q("""SELECT SUM(revised) FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=9 AND fund='0100' AND account_type='revenue'"""),
          -52215332.0, tol=192.0)
    check(db, 'general fund revenue received, FY26 P9',
          q("""SELECT SUM(expended) FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=9 AND fund='0100' AND account_type='revenue'"""),
          -38858712.04)
    # Chapter 70, which the model projects separately and which no expense line can see.
    check(db, 'Chapter 70 aid budgeted FY26 (object 450600)',
          q("""SELECT -revised FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=9 AND object='450600'"""),
          9229410.0)

    # The workbook's FY25 halves, and the difference this project has published.
    check(db, 'workbook FY25 actuals, 351 line rows',
          q("""SELECT SUM(value) FROM workbook_figure
               WHERE fy=2025 AND column_kind='actual' AND row_kind='line'"""),
          24560511.30)
    check(db, 'workbook FY25 budget, 351 line rows',
          q("""SELECT SUM(value) FROM workbook_figure
               WHERE fy=2025 AND column_kind='budget' AND row_kind='line'"""),
          25321760.0)
    check(db, 'workbook FY25 under budget',
          q("""SELECT SUM(CASE WHEN column_kind='budget' THEN value ELSE -value END)
               FROM workbook_figure WHERE fy=2025 AND row_kind='line'
                 AND column_kind IN ('budget','actual')"""),
          761248.70)
    # Rule 13: reconcile the line sum to the total the sheet itself prints (row 404),
    # never to our own sum of the lines.
    check(db, 'FY25 actuals: line sum vs the sheet\'s own printed total',
          q("""SELECT (SELECT SUM(value) FROM workbook_figure
                      WHERE fy=2025 AND column_kind='actual' AND row_kind='line')
                   - (SELECT value FROM workbook_figure
                      WHERE fy=2025 AND column_kind='actual' AND row=404)"""),
          0.0)

    # The workbook's FY26 budget column ties to the town's FY26 original appropriation
    # for departments 300 + 301. That is what establishes the base our figures measure
    # off: the appropriation as voted, before transfers and with no encumbrances.
    check(db, 'workbook FY26 final budget vs town approp 300+301',
          q("""SELECT SUM(value) FROM workbook_figure
               WHERE fy=2026 AND column_kind='final_budget' AND row_kind='line'""")
          - q("""SELECT SUM(original) FROM ledger_snapshot
                 WHERE account_id IN ('0100-300','0100-301') AND period=9"""),
          0.0, tol=2.0)

    # THE $105,282 "GAP", WHICH WAS NEITHER $105,282 NOR A GAP.
    #
    # The handoff carried an open question: the district's FY26 budget was $105,282 below
    # the town's appropriation, and we did not know whether that was fee netting (rule 11)
    # or missing lines. It was neither. It was two wrong comparisons stacked:
    #
    #   1. It measured against department 300 alone. The town's school appropriation is
    #      300 + 301, and 301 SCHOOL NON-RECURRING EXPENSES is $40,000 of it.
    #   2. It used `budget_figure` stage `settled`, which is extracted from the district's
    #      FINAL BUDGET DOCUMENT -- a different document from the FY27 workbook, about the
    #      same year. The check above shows the WORKBOOK ties to the appropriation within
    #      $1.93. The budget document does not, and the difference is between two things
    #      the district published, not between a budget and a vote.
    #
    # So this asserts the second difference is fully ITEMISED rather than merely measured.
    # Four labels the workbook carries and the budget document does not, and one line the
    # two documents state differently, account for all of it:
    #
    #     98,784.00  E.S. Psychologist          40,000.00  Curriculum Adoption
    #      6,500.00  Dues/Meetings                   0.00  two lines carrying zero
    #
    # A check on the total alone would pass while a new discrepancy appeared and an old
    # one vanished by the same amount -- compensating errors, which this project has
    # shipped before. So the residual is what is asserted, and it is pennies.
    #
    # The E.S. Psychologist is worth noting and NOT worth explaining here. It is also one
    # of only five nonzero lines in FY26 `proposed` that `settled` does not carry. That
    # the position was cut is a HYPOTHESIS the two documents are consistent with; nothing
    # in them tests it, and the roster would not settle it either -- it has no FTE.
    import re as _re

    def _norm(x):
        return _re.sub(r'[^a-z0-9]', '', (x or '').lower())

    def _bag(sql):
        out = {}
        for lab, val in db.execute(sql):
            out[_norm(lab)] = out.get(_norm(lab), 0.0) + (val or 0.0)
        return out

    _wb = _bag("""SELECT b.label, w.value FROM workbook_figure w
                  LEFT JOIN budget_line b USING (line_key)
                  WHERE w.fy=2026 AND w.column_kind='final_budget' AND w.row_kind='line'""")
    _bd = _bag("""SELECT label, value FROM budget_figure
                  WHERE fy=2026 AND stage='settled'""")
    # The discrepancies we have actually looked at, ENUMERATED. Subtracting a residual
    # computed from the same two bags would be an identity -- it would restate the
    # difference as itself and pass forever. These are typed because they are findings.
    _KNOWN_FY26 = {
        'espsychologist': 98784.00,     # in the workbook, absent from the budget document
        'curriculumadoption': 40000.00,  # ditto
        'duesmeetings': 6500.00,        # both documents carry it, stated differently
    }
    _residual = sum(_wb.values()) - sum(_bd.values()) - sum(_KNOWN_FY26.values())
    check(db, 'FY26 workbook vs district budget document, residual after 3 known lines',
          _residual, 0.0, tol=1.0)   # a dollar: eight P.S. supply lines round differently
    # ...and each known line is still the discrepancy we recorded, not a number that
    # happens to sum right. Compensating errors are how this project has been fooled
    # before, and a total is exactly what hides them.
    for _k, _amt in _KNOWN_FY26.items():
        check(db, 'FY26 discrepancy still stands: %s' % _k,
              _wb.get(_k, 0.0) - _bd.get(_k, 0.0), _amt, tol=0.01)

    # The first ACCOUNT-LEVEL general fund expenditure report in the archive: FY26 at
    # period 12, sent by the Town Manager on 2 September 2026. Asserted against the
    # printed PDF's own GRAND TOTAL, which is the only thing establishing that the
    # spreadsheet and the printout are one report -- the spreadsheet states no period.
    check(db, 'FY26 P12 expended, all departments (spreadsheet vs printed total)',
          q("""SELECT SUM(expended) FROM ledger_snapshot JOIN account USING (account_id)
               WHERE fy=2026 AND period=12 AND fund='0100'"""),
          52163984.85)
    check(db, 'FY26 P12 school department, 258 accounts, unspent',
          q("""SELECT ROUND(SUM(available),2) FROM ledger_snapshot
                 JOIN account USING (account_id)
               WHERE fy=2026 AND period=12 AND dept='300'"""),
          482101.12)

    # The town's own FY25 closing figure, quoted rather than derived. Asserted because a
    # figure this project quotes must not drift by a cent, and because the gap between it
    # and our own subtraction is the point of the table that shows them together.
    check(db, "the town's stated FY25 surplus, as closed",
          q("""SELECT amount FROM stated_figure
               WHERE fy=2025 AND metric='school_surplus' AND supersedes IS NOT NULL"""),
          603885.97)
    check(db, 'our restatement subtraction, minus the town figure',
          q("""SELECT (SELECT SUM(CASE WHEN column_kind='budget' THEN value ELSE -value END)
                      FROM workbook_figure WHERE fy=2025 AND row_kind='line'
                        AND column_kind IN ('budget','actual'))
                   - (SELECT amount FROM stated_figure WHERE fy=2025
                      AND metric='school_surplus' AND supersedes IS NOT NULL)"""),
          157362.73)

    # DESE's all-funds per-pupil total for Lunenburg, asserted against the ten function
    # components DESE prints beside it. An independent publisher's arithmetic, checked
    # rather than trusted.
    check(db, 'DESE FY25 Lunenburg in-district per pupil, components vs total',
          q("""SELECT (SELECT SUM(value) FROM dese_measure
                      WHERE lea='01620000' AND fy=2025 AND "group"='Expenditures Per Pupil'
                        AND measure NOT LIKE 'Total%')
                   - (SELECT value FROM dese_measure WHERE lea='01620000' AND fy=2025
                      AND measure='Total In-District Expenditures')"""),
          0.0, tol=10.0)

    # DESE's function-code split, SY2025 Lunenburg. Asserted against the figures the
    # source itself prints, and against the OTHER DESE publication already in this
    # database -- two independent DESE routes to the same per-pupil total.
    check(db, 'DESE FY25 Lunenburg in-district spending, all funds',
          q("""SELECT total FROM dese_function_expenditure
               WHERE lea='01620000' AND fy=2025 AND func_cat_code='IIII'"""),
          27903187.0)
    check(db, 'DESE FY25 Lunenburg in-district, general fund only',
          q("""SELECT gen_fund FROM dese_function_expenditure
               WHERE lea='01620000' AND fy=2025 AND func_cat_code='IIII'"""),
          25331940.0)
    check(db, 'DESE FY25 Lunenburg in-district, grants and revolving',
          q("""SELECT grants_revolving FROM dese_function_expenditure
               WHERE lea='01620000' AND fy=2025 AND func_cat_code='IIII'"""),
          2571247.0)
    # The hierarchy, asserted in SQL rather than only in the extract: the grand total is
    # the two rollups and nothing else. If `level` were wrong this would not hold.
    check(db, 'DESE FY25 Lunenburg, IIII + OODD - TTPP',
          q("""SELECT (SELECT SUM(total) FROM dese_function_expenditure
                       WHERE lea='01620000' AND fy=2025 AND level='rollup')
                    - (SELECT total FROM dese_function_expenditure
                       WHERE lea='01620000' AND fy=2025 AND level='total')"""),
          0.0, tol=4.0)
    # ...and the in-district detail rows reach the in-district rollup, which is the join
    # that would silently match nothing if `level` or `in_out_dist` were lost.
    check(db, 'DESE FY25 Lunenburg, in-district detail vs the IIII rollup',
          q("""SELECT (SELECT SUM(total) FROM dese_function_expenditure
                       WHERE lea='01620000' AND fy=2025 AND level='detail'
                         AND in_out_dist='In-District')
                    - (SELECT total FROM dese_function_expenditure
                       WHERE lea='01620000' AND fy=2025 AND func_cat_code='IIII')"""),
          0.0, tol=10.0)
    # The paraprofessional line, which is the one this dataset was fetched for. Rule 11:
    # this is a FUNCTION CODE, not a budget line and not a post -- see money_gaps.
    check(db, 'DESE FY25 Lunenburg paras (fn 2330), grants and revolving',
          q("""SELECT grants_revolving FROM dese_function_expenditure
               WHERE lea='01620000' AND fy=2025 AND func_code='2330'"""),
          478097.0)
    check(db, 'DESE FY25 Lunenburg paras (fn 2330), general fund',
          q("""SELECT gen_fund FROM dese_function_expenditure
               WHERE lea='01620000' AND fy=2025 AND func_code='2330'"""),
          1338477.0)
    # Two DESE publications, one workbook and one open-data dataset, on the same figure.
    check(db, 'DESE FY25 per pupil: function dataset vs RADAR workbook',
          q("""SELECT (SELECT per_pupil FROM dese_function_expenditure
                       WHERE lea='01620000' AND fy=2025 AND func_cat_code='IIII')
                    - (SELECT value FROM dese_measure WHERE lea='01620000' AND fy=2025
                       AND measure='Total In-District Expenditures')"""),
          0.0)
    # The peer denominator. A rank with no denominator is not a measurement.
    check(db, 'districts in the FY25 statewide total distribution',
          q("""SELECT districts FROM dese_function_statewide
               WHERE fy=2025 AND level='total' AND func_cat_code='TTPP'"""),
          318.0)


    # ---------------------------------------------------------------- DESE, ingested
    # 8 September 2026. Fourteen datasets. Every check below asserts a NUMBER derived
    # from the data, never that a row or a string exists.

    # THE ONE THAT MATTERS MOST: the state's Chapter 70 formula against the TOWN'S OWN
    # general ledger. DESE's DataC70 sheet and a MUNIS revenue printout, neither derived
    # from the other, on one receipt.
    check(db, "FY2026 Chapter 70 aid: DESE's formula minus the town's own ledger",
          q("""SELECT (SELECT ch70_aid FROM dese_ch70_formula
                       WHERE lea='01620000' AND fy=2026)
                    - (SELECT -revised FROM ledger_snapshot JOIN account USING (account_id)
                       WHERE fy=2026 AND period=9 AND object='450600')"""),
          0.0, tol=1.0)

    # The formula's own arithmetic, in SQL rather than only in the extract.
    check(db, 'FY2026 Lunenburg required NSS - (local contribution + Chapter 70 aid)',
          q("""SELECT required_nss - (required_local_contribution + ch70_aid)
               FROM dese_ch70_formula WHERE lea='01620000' AND fy=2026"""),
          0.0, tol=1.0)
    # Two different quantities under one column name in the source. If this ever came out
    # zero the split would have collapsed and `required_nss` would silently be one number.
    check(db, 'district-years where the two rqdnss columns differ (must not be zero)',
          q("""SELECT COUNT(*) > 0 FROM dese_ch70_formula
               WHERE required_nss IS NOT NULL AND required_nss_published IS NOT NULL
                 AND ABS(required_nss - required_nss_published) > 1"""),
          1.0)
    # Rule 1, asserted: the last two years of net school spending are BUDGETED, and the
    # source column that holds them is headed `actualNSS`.
    check(db, 'FY2026 net school spending rows whose stage is not `actual`',
          q("""SELECT COUNT(*) FROM dese_ch70_formula
               WHERE fy=2026 AND net_school_spending IS NOT NULL
                 AND nss_stage <> 'budgeted'"""),
          0.0)

    # Lunenburg above the required floor. Published as the measurement, never as a verdict:
    # the floor is a minimum, not a standard of adequacy.
    check(db, 'FY2026 Lunenburg net school spending as a share of required',
          q("""SELECT ROUND(net_school_spending / required_nss_published, 3)
               FROM dese_ch70_formula WHERE lea='01620000' AND fy=2026"""),
          1.2, tol=0.15)

    # Where Lunenburg sits, with the denominator. A rank with no denominator is not a
    # measurement, so the check asserts the denominator too.
    check(db, 'FY2026 districts in the net-school-spending distribution',
          q("""SELECT districts > 300 FROM dese_ch70_statewide
               WHERE fy=2026 AND measure='net school spending as a share of required'"""),
          1.0)
    check(db, "FY2026 Lunenburg's share of required, distribution vs the formula table",
          q("""SELECT (SELECT lunenburg FROM dese_ch70_statewide WHERE fy=2026
                       AND measure='net school spending as a share of required')
                    - (SELECT net_school_spending / required_nss_published
                       FROM dese_ch70_formula WHERE lea='01620000' AND fy=2026)"""),
          0.0, tol=0.0002)

    # The circuit breaker, and the identity it states about itself.
    check(db, 'FY2026 Lunenburg circuit breaker: tuition + transport - total net claim',
          q("""SELECT net_eligible_instruction_tuition + net_eligible_transport
                      - total_net_claim
               FROM dese_circuit_breaker WHERE lea='01620000' AND fy=2026"""),
          0.0, tol=1.0)
    check(db, 'FY2026 Lunenburg high-cost special education students claimed > 0',
          q("""SELECT eligible_students_claimed > 0 FROM dese_circuit_breaker
               WHERE lea='01620000' AND fy=2026"""), 1.0)

    # Staffing. The rollup and the detail, in one table, asserted apart.
    check(db, 'SY2026 Lunenburg teacher FTE: the four program areas minus the total',
          q("""SELECT gen_ed_fte + sped_fte + career_tech_fte + el_fte - total_fte
               FROM dese_teacher_program_area
               WHERE lea='01620000' AND fy=2026 AND org_level='district'"""),
          0.0, tol=0.25)
    # Two DESE datasets on one quantity: program area against grade-and-subject.
    check(db, 'SY2026 Lunenburg district FTE: program area minus grade-and-subject',
          q("""SELECT (SELECT total_fte FROM dese_teacher_program_area
                       WHERE lea='01620000' AND fy=2026 AND org_level='district')
                    - (SELECT total_fte FROM dese_teacher_grade_subject
                       WHERE lea='01620000' AND fy=2026 AND org_level='district'
                         AND subject='All')"""),
          0.0, tol=0.15)
    # ...and the grade bands within it.
    check(db, 'SY2026 Lunenburg: the six grade bands minus the total FTE',
          q("""SELECT pk_2_fte + grade_3_5_fte + grade_6_8_fte + grade_9_12_fte
                      + multi_grade_fte + all_grade_fte - total_fte
               FROM dese_teacher_grade_subject
               WHERE lea='01620000' AND fy=2026 AND org_level='district'
                 AND subject='All'"""),
          0.0, tol=0.35)
    # The rollup trap itself, in the table that carries it: summing every subject would
    # count each teacher roughly three times. This asserts that it WOULD, so that a build
    # which had lost `subject_level` fails here rather than in somebody's query.
    check(db, 'SY2026 Lunenburg: every subject summed, over the `All` row (must exceed 2x)',
          q("""SELECT (SELECT SUM(total_fte) FROM dese_teacher_grade_subject
                       WHERE lea='01620000' AND fy=2026 AND org_level='district')
                    / (SELECT total_fte FROM dese_teacher_grade_subject
                       WHERE lea='01620000' AND fy=2026 AND org_level='district'
                         AND subject='All') > 2"""),
          1.0)
    # Headcount, not FTE, and the only published count of paraprofessionals as people.
    # NOTE THE FIGURE. `notes/DATA-TO-INGEST.md` recorded 118 paraprofessionals and 38
    # administrators for SY2023 from this dataset. Both are exactly TWICE what it holds,
    # because `All Educators` is a total row sitting beside the seven reported races and
    # a first reading summed both. That is the rollup-beside-detail trap this whole
    # ingest is organised around, committed once already in our own notes -- so the check
    # asserts the total AND that the naive sum is exactly double it, which is the shape a
    # lost level column would take.
    check(db, 'SY2023 Lunenburg paraprofessional HEADCOUNT (the All Educators row)',
          q("""SELECT educators_headcount FROM dese_educator_workforce
               WHERE lea='01620000' AND fy=2023 AND job_class='Paraprofessional'
                 AND race_level='all'"""),
          59.0)
    check(db, 'SY2023 paras: summing every row over the total row (the double count)',
          q("""SELECT (SELECT SUM(educators_headcount) FROM dese_educator_workforce
                       WHERE lea='01620000' AND fy=2023
                         AND job_class='Paraprofessional')
                    / (SELECT educators_headcount FROM dese_educator_workforce
                       WHERE lea='01620000' AND fy=2023
                         AND job_class='Paraprofessional' AND race_level='all')"""),
          2.0)

    # Students. The published SWD count, which used to be reachable only by multiplying a
    # percentage by enrollment -- our arithmetic, not a published figure.
    check(db, 'SY2026 Lunenburg students with disabilities, as n62c-bx65 publishes it',
          q("""SELECT measure_cnt FROM dese_sped_program
               WHERE lea='01620000' AND fy=2026 AND indicator_category='Disability Type'
                 AND indicator_level='total'"""),
          258.0)
    # The same quantity out of three DESE datasets. Two of them agree exactly:
    check(db, 'SY2026 Lunenburg SWD: the sped file minus the enrollment file',
          q("""SELECT (SELECT measure_cnt FROM dese_sped_program
                       WHERE lea='01620000' AND fy=2026
                         AND indicator_category='Disability Type'
                         AND indicator_level='total')
                    - (SELECT swd_cnt FROM dese_enrollment
                       WHERE lea='01620000' AND fy=2026 AND org_level='district')"""),
          0.0)
    # ...AND THE THIRD DOES NOT, INSIDE A SINGLE FILE. In `yamx-769q` the CONTEXT rows
    # count 258 students with disabilities and the SPECIAL EDUCATION STAFF rows carry 246
    # as the denominator of their per-100 ratios. One dataset, one district, one year, two
    # counts of the same children. This asserts the gap so it cannot quietly close: the
    # paraprofessional-per-FTE chain in notes/DATA-TO-INGEST.md is built on the 246.
    check(db, 'SY2026 Lunenburg SWD inside yamx-769q: staff denominator minus context',
          q("""SELECT (SELECT DISTINCT measure_cnt FROM dese_sped_indicator
                       WHERE lea='01620000' AND fy=2026
                         AND indicator_category='SPECIAL EDUCATION STAFF')
                    - (SELECT measure_cnt FROM dese_sped_indicator
                       WHERE lea='01620000' AND fy=2026 AND indicator_category='CONTEXT'
                         AND grades='K-12'
                         AND student_group='Students with Disabilities')"""),
          -12.0)
    check(db, 'SY2026 Lunenburg enrollment: PK to 12 plus SP, minus the printed total',
          q("""SELECT pk_cnt + k_cnt + grade_1_cnt + grade_2_cnt + grade_3_cnt
                      + grade_4_cnt + grade_5_cnt + grade_6_cnt + grade_7_cnt
                      + grade_8_cnt + grade_9_cnt + grade_10_cnt + grade_11_cnt
                      + grade_12_cnt + sp_cnt - total_cnt
               FROM dese_enrollment
               WHERE lea='01620000' AND fy=2026 AND org_level='district'"""),
          0.0)
    # School choice, both directions, out of ONE table.
    check(db, 'SY2026 Lunenburg children leaving via school choice',
          q("""SELECT SUM(students) FROM dese_town_enrollment
               WHERE fy=2026 AND town='Lunenburg' AND lea <> '01620000'
                 AND enrollment_reason='School Choice Program'"""),
          58.0)
    check(db, 'SY2026 children arriving in Lunenburg via school choice',
          q("""SELECT SUM(students) FROM dese_town_enrollment
               WHERE fy=2026 AND lea='01620000' AND town <> 'Lunenburg'
                 AND enrollment_reason='School Choice Program'"""),
          11.0)
    # The carried-forward year. This must keep firing: it is the reason the column exists.
    check(db, 'Lunenburg movement rows repeating the previous year exactly',
          q("""SELECT COUNT(*) > 0 FROM dese_sped_movement
               WHERE lea='01620000' AND repeats_prior_year='yes'"""),
          1.0)
    # The placement trajectory, whose bases are tiny: this asserts the COUNT, because a
    # percentage off a base of tens must never travel alone.
    check(db, 'SY2026 Lunenburg K-12 cohort starting substantially separate',
          q("""SELECT cohort_cnt FROM dese_sped_trajectory
               WHERE lea='01620000' AND fy=2026 AND grade_span='K-12'
                 AND placement_at_start='Substantially Separate Classroom'"""),
          28.0)

    # Every DESE fact carries an address.
    check(db, 'DESE staffing rows with no document', q(
        "SELECT COUNT(*) FROM dese_teacher_grade_subject "
        "WHERE doc_id IS NULL OR doc_id=''"), 0)
    check(db, 'Chapter 70 rows with no document', q(
        "SELECT COUNT(*) FROM dese_ch70_formula WHERE doc_id IS NULL OR doc_id=''"), 0)

    # Every fact carries an address.
    check(db, 'ledger rows with no document', q(
        "SELECT COUNT(*) FROM ledger_snapshot WHERE doc_id IS NULL OR doc_id=''"), 0)
    check(db, 'workbook rows with no document', q(
        "SELECT COUNT(*) FROM workbook_figure WHERE doc_id IS NULL OR doc_id=''"), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail the build if a reconciliation does not tie')
    args = ap.parse_args()

    if os.path.exists(DB):
        os.remove(DB)                     # rebuilt from scratch, always
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    db.executemany('INSERT INTO fiscal_period VALUES (?,?,?,?)', PERIODS)

    print('Building %s' % os.path.relpath(DB, ROOT))
    docs = load_documents(db)
    print('  accounts         %5d' % load_munis(db))
    print('  funds            %5d' % db.execute(
        'SELECT COUNT(*) FROM fund').fetchone()[0])
    print('  ledger snapshots %5d' % db.execute(
        'SELECT COUNT(*) FROM ledger_snapshot').fetchone()[0])
    print('  budget figures   %5d' % load_budget_figures(db))
    print('  workbook figures %5d' % load_workbook(db))
    print('  budget lines     %5d' % db.execute(
        'SELECT COUNT(*) FROM budget_line').fetchone()[0])
    fa, gr, st, ds = load_funds(db)
    print('  fund activity    %5d' % fa)
    print('  grant awards     %5d' % gr)
    print('  stated figures   %5d' % st)
    print('  DESE measures    %5d' % ds)
    nfn, nsw = load_dese_function(db)
    print('  DESE by function %5d  (+ %d statewide distribution rows)' % (nfn, nsw))
    print('  DESE staffing,   %5d  (%d tables: teachers, students, Chapter 70)'
          % (load_dese_datasets(db), len(DESE_DATASETS)))
    print('  reference rows   %5d' % load_reference(db))
    print('  provenance rows  %5d' % load_provenance(db))
    print('  role vocabulary  %5d' % load_role_classification(db))
    print('  money model      %5d' % load_money_model(db))
    print('  newly loaded     %5d' % load_unloaded(db))
    check_document_paths(db)

    # Documents last: every doc_id any fact cites is known by now, so an orphan can be
    # stubbed and counted rather than silently producing a figure with no address.
    cited = [r[0] for r in db.execute(
        """SELECT DISTINCT doc_id FROM ledger_snapshot
           UNION SELECT DISTINCT doc_id FROM workbook_figure
           UNION SELECT DISTINCT doc_id FROM dese_measure
           UNION SELECT DISTINCT doc_id FROM dese_function_expenditure
           UNION SELECT DISTINCT doc_id FROM dese_teacher_program_area
           UNION SELECT DISTINCT doc_id FROM dese_teacher_subject
           UNION SELECT DISTINCT doc_id FROM dese_teacher_grade_subject
           UNION SELECT DISTINCT doc_id FROM dese_educator_workforce
           UNION SELECT DISTINCT doc_id FROM dese_enrollment
           UNION SELECT DISTINCT doc_id FROM dese_sped_indicator
           UNION SELECT DISTINCT doc_id FROM dese_sped_program
           UNION SELECT DISTINCT doc_id FROM dese_sped_trajectory
           UNION SELECT DISTINCT doc_id FROM dese_sped_movement
           UNION SELECT DISTINCT doc_id_sending FROM dese_town_enrollment
           UNION SELECT DISTINCT doc_id_receiving FROM dese_town_enrollment
           UNION SELECT DISTINCT doc_id FROM dese_ch70_formula
           UNION SELECT DISTINCT doc_id FROM dese_ch70_aid_factor
           UNION SELECT DISTINCT doc_id FROM dese_ch70_contribution
           UNION SELECT DISTINCT doc_id FROM dese_circuit_breaker
           UNION SELECT DISTINCT doc_id FROM stated_figure
           UNION SELECT DISTINCT doc_id FROM fund_activity""")]
    n_docs, hashed = finish_documents(db, docs, cited)
    print('  documents        %5d  (%d hashed from disk)' % (n_docs, hashed))
    db.executescript(VIEWS)
    db.commit()

    fixed, missing, unresolved = resolve_budget_documents(db)
    print('  budget provenance      %d source name(s) resolved to a document; '
          '%d figures still unresolved' % (fixed, unresolved))
    for m in missing[:5]:
        print('      no document for %s' % m)

    n_text_fy = check_fy_types(db)
    print('  fy typing              every fy is INTEGER except %d documented exception(s)'
          % n_text_fy)

    coded, overlap = check_join_key(db)
    print('  function codes   %5d accounts carry one; %d shared with the budget' %
          (coded, overlap))

    n_st = check_no_stage_actual(db)
    print('  stage names      %5d tables carry a stage; none of them calls it `actual`'
          % n_st)

    n_q = check_stored_queries(db)
    print('  worked examples  %5d published queries, every one executed against this '
          'build' % n_q)

    reconcile(db)
    bad = [c for c in CHECKS if not c[0]]
    print('\n%d of %d reconciliations tie' % (len(CHECKS) - len(bad), len(CHECKS)))

    # The crosswalk is empty and that is the honest state, not an oversight.
    mapped = db.execute('SELECT COUNT(*) FROM crosswalk').fetchone()[0]
    lines = db.execute('SELECT COUNT(*) FROM budget_line').fetchone()[0]
    print('crosswalk: %d of %d budget lines mapped to a single account.' % (mapped, lines))
    print('A LINE still cannot be traced into the ledger, and that is a property of the\n'
          'data rather than a gap in the load: MUNIS truncates account names to ten\n'
          'characters, so MS GUIDANC and HS GUIDANC are both 2710 where the budget has a\n'
          'row per school. What CAN be traced is the CATEGORY, through account.function --\n'
          'see v_function_budget_vs_ledger. Populating crosswalk from that would record an\n'
          'inference as a mapping, so it stays empty and the view does the joining.')

    db.close()
    if args.check and bad:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
