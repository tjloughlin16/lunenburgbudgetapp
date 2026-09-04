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
                    Stage is what the figure IS: proposed / settled / actual. A stage is
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
    stage               TEXT NOT NULL       -- 'proposed' | 'settled' | 'actual'
        CHECK (stage IN ('proposed', 'settled', 'actual')),
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
    'rate-register', 'sped-para-history',
    'sped-teacher-history', 'sped-transport-history', 'total-expenses-history',
    'total-salaries-history', 'variance-by-group',
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
CREATE VIEW v_transfer_history AS
SELECT  a.dept, a.name, l.fy, l.period, l.original, l.transfers, l.revised,
        l.transfers - LAG(l.transfers) OVER (
            PARTITION BY l.account_id, l.fy ORDER BY l.period) AS moved_since_last,
        l.doc_id
FROM    ledger_snapshot l JOIN account a USING (account_id)
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
WHERE   p.is_final = 0;

-- Budget against actual for a single line, from the district's own documents.
-- Both halves are read from the same document, which is what makes the pair sound;
-- these lines do NOT sum back to the district totals, so never apportion with this.
CREATE VIEW v_line_budget_vs_actual AS
SELECT  b.line_key, b.label, b.fy,
        MAX(CASE WHEN b.stage = 'settled'  THEN b.value END) AS settled,
        MAX(CASE WHEN b.stage = 'proposed' THEN b.value END) AS proposed,
        MAX(CASE WHEN b.stage = 'actual'   THEN b.value END) AS actual,
        MAX(b.documents_disagree)                            AS documents_disagree
FROM    budget_figure b
-- variant = '' or a scenario column would win the MAX and be reported as the year's
-- budget. A document stating four FY27 proposals states four figures, not one.
WHERE   b.variant = ''
GROUP BY b.line_key, b.label, b.fy;

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
    link = {r['path']: r for r in rows('link-status')}
    copy = {r['path']: r for r in rows('copy-status')}

    # The crawlers' own indexes carry the upstream URL and the sha256 taken at fetch time.
    crawled = {}
    for name in ('dese', 'district-budget-page', 'town-site'):
        path = os.path.join(ROOT, 'sources', name, 'index.csv')
        if not os.path.exists(path):
            continue
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
    for p, cr in crawled.items():
        if p not in out:
            out[p] = [p, p, 'primary', None, None, None, cr.get('upstream'),
                      None, None, None, cr.get('sha256')]

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


TOWN_LEDGER_DOC = 'sources/q3-fy26/town-general-fund-expenditures-fy26-q3.txt'
WORKBOOK_DOC = 'sources/xlsx/fy27-proposals.xlsx'
FUNDS_DOC = 'sources/xlsx/school-funds-fy26.xlsx'
SPECIAL_REV_DOC = 'sources/q3-fy26/town-special-revenue-fy26-q3.xlsx'

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
    """
    out, lines = [], {}
    for r in rows('line-history'):
        fy, value = r['fy'], num(r['value'])
        if (not fy.isdigit() or value is None
                or r['stage'] not in ('proposed', 'settled', 'actual')):
            continue
        out.append((r['key'], r['label'], int(fy), r['stage'], r.get('variant', ''),
                    value, int(r['documents_disagree'] or 0), r['source']))
        lines.setdefault(r['key'], r['label'])
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
        db.execute('CREATE TABLE "%s" (%s)' % (table, ', '.join(c + ' TEXT' for c in safe)))
        db.executemany('INSERT INTO "%s" VALUES (%s)' % (table, ','.join('?' * len(cols))),
                       [[r[c] for c in cols] for r in data])
        n += len(data)
    return n


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
    print('  reference rows   %5d' % load_reference(db))

    # Documents last: every doc_id any fact cites is known by now, so an orphan can be
    # stubbed and counted rather than silently producing a figure with no address.
    cited = [r[0] for r in db.execute(
        """SELECT DISTINCT doc_id FROM ledger_snapshot
           UNION SELECT DISTINCT doc_id FROM workbook_figure
           UNION SELECT DISTINCT doc_id FROM dese_measure
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

    coded, overlap = check_join_key(db)
    print('  function codes   %5d accounts carry one; %d shared with the budget' %
          (coded, overlap))

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
