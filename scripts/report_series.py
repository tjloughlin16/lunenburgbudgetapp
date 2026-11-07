#!/usr/bin/env python3
"""Year-by-year series read out of the annual town reports, one family at a time.

Most of what the reports print over time is prose or a short list, in a layout that changes
every few years, so no table reader gets it. A family is therefore READ, by a person or an
agent, into `sources/data/report-series/<family>.csv`, and this script is what stops a read
being taken on trust (CLAUDE.md rules 13, 13c):

  * every row quotes the page, and the quote must be on the cited page of the edition's text;
  * every figure in `value` must be in its quote, unless the row says it was spelled out;
  * where the page prints a total, the parts are summed and compared. A year that does not
    tie is LABELLED with the residual, never dropped and never adjusted;
  * `<family>.coverage.csv` holds one row per edition: `held`, or `not printed` with the
    pages looked at. An edition with neither is a hole, and the build refuses (rule 13c:
    a pattern that found nothing is not an absence).

It writes `sources/data/series-<family>.csv`, which build_db.py loads by glob, and
`sources/data/series-coverage.csv`, one row per family per edition.

    python3 scripts/report_series.py            # rebuild every family
    python3 scripts/report_series.py --check    # fail if a read fails or an output is stale
    python3 scripts/report_series.py --find REGEX        # every edition, page and line that matches
    python3 scripts/report_series.py --page 1975 32      # one page's text, every layer we hold

`our_grouping` is ours and says so in its name: the town's category names change by era, and
a grouping across them is a judgement, not something the reports print.
"""
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READS = os.path.join(ROOT, 'sources', 'data', 'report-series')
DATA = os.path.join(ROOT, 'sources', 'data')
TEXT = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')
BUDGET_PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')

READ_COLS = ['year', 'year_basis', 'edition', 'pdf_page', 'row_group', 'row_role', 'measure', 'value',
             'unit', 'our_grouping', 'quote', 'note']
OUT_COLS = READ_COLS + ['group_parts_sum', 'group_total_printed', 'group_ties', 'quote_found']
COVERAGE_COLS = ['family', 'edition', 'status', 'pages_looked', 'note']
ROLES = {'total', 'part', 'single'}
TIES_TOLERANCE = 0.005  # below a cent; a count either ties or it does not

# Every family says what it is, for the source catalogue (build_source_index.py).
FAMILIES = {
    'office-hours-directories': ('Office hours and phone directories',
                   'Town office hours by office from the front matter of every edition 1959-FY2013, the telephone directories by subject 1962-2010 and FY2012, the FY2014-FY2025 office hours and telephone number tables, and hours stated in department reports; office, hours or number as printed in the quote, value blank.'),
    'enrolment-2006': ('School enrolment by grade, 2006 gap',
                   'Grade-by-school enrolment tables as of October 1: this pass adds only the one 2006 page-36 cell (Grade 10, 10/02/06) that report-enrollment-mcas leaves blank; the other 2006 cells are held there.'),
    'trust-fund-holdings': ('Trust fund holdings by bank, 1961-FY2025',
                   'The Trust Fund Commission\'s Investment of Funds pages: for each trust fund (library, sidewalks and grounds, worthy poor, cemetery perpetual care and later funds) '
                   'the donor, bank, passbook or certificate number and amount as printed, with the fund totals and summary of funds. Read from the page images because the '
                   'side-by-side fund panels cannot be read from the text layer. Bank subtotals are rows that add to nothing.'),
    'trade-permits': ('Plumbing, gas and wiring permits, inspections and fees, 1961-FY2022',
                   'The Plumbing, Gas Fitting and Wiring Inspectors\' counts of permits and inspections and fees collected (1961-2001, as each report words them) and the permit fee lines in the Detailed Statement of Receipts (plumbing 1960-FY2022, gas fitting from 1964, wiring from 1982). '
                   'Plumbing, gas and wiring are kept as separate measures; combined plumbing-and-gas counts are kept as printed; FY2019-FY2025 counts are in building-activity.csv.'),
    'conservation-filings': ('Conservation Commission filings, decisions, hearings and wetlands fees, 1972-FY2025',
                   'The Conservation Commission counts the reports print in prose (hearings, requests for determination, Notices of Intent, Orders of Conditions, determinations, Certificates of Compliance, enforcement orders, inspections; 1972-2007 and FY2024-FY2025) and the wetlands filing, advertising and bylaw fee lines in the Detailed Statement of Receipts (1973-FY2022). '
                   'The wording changes by year (hearings, requests for determination, Wetland Determinations, Determinations of Applicability, Administrative Determinations) and each is kept as printed; counts are what the page counts, with some partial-year or caveated.'),
    'pay-grades-fy2011': ('Pay grades by class title, FY2011 and FY2015, and 1984 pay rates',
                   'The Classification Plan lists of class title and grade the report prints (FY2011 p89, FY2015 Schedule A), and the 1984 amended hourly, weekly and yearly rates by year of service, as printed. '
                   'The 2010 list is in report-classification-plan.csv; the grade-and-step salary schedules are in salary-schedule.csv.'),
    'classification-schedules': ('Town classification and salary schedules: class, step and printed rate, 1966-1973 and the FY2011 pay schedule',
                   'The Classification and Salary Schedule the town reports print 1966-1973 (nine full schedules, dated March 1967 to July 1974), one row per class and step or rate column, with the rates printed in the text of the police rate votes of 1972, 1974 and 1976, and the 2010 report\'s grade-and-step pay schedule for fiscal 2011. '
                   'Figures are printed in different bases (annual, hourly, weekly or per-year payments, some with no period printed) and are not comparable across them; a rate printed once for a bracketed group of classes is repeated on a row for each class. '
                   'Later schedules (1974-2009) were printed in the Finance Committee report, not the town report; 1984 and the class-title lists are in pay-grades-fy2011.csv, FY2015, FY2016 and FY2022 grade-and-step schedules are in salary-schedule.csv.'),
    'births-census': ('Births recorded and census counts, 1945-FY2025',
                   'The births the Town Clerk\'s report prints (a chart or tabulation: 1950-1959, 1961, 1965, 1963-1973, 1970-1981) and the dated census populations '
                   'the school Statistics page prints (1945 to the State census of 1971), as printed in each edition, plus the Town Clerk\'s printed birth totals (1976, 2008-FY2025 editions). Later census populations are in series-town-facts.csv. Not the names in the vital-records lists, and not the ACS (census-acs.csv).'),
    'monty-tech-enrollment': ('Monty Tech enrolment of Lunenburg students, 1971-FY2016',
                   'How many Lunenburg students the Montachusett Regional Vocational Technical School report or the School Committee report prints as enrolled: the member-town list '
                   'in the school\'s annual report (2002-FY2016, on October 1 or, FY2014-FY2016, June 1), plus the 1971 entrants and the 1973 students sent. '
                   'Not the DESE enrolment file (dese-enrollment.csv), and no school-wide totals or shop lists.'),
    'veterans-services': ('Veterans services: recipients and dollars paid, 1959-FY2025',
                   'The counts and dollars the Veterans\' Agent or Veterans Services Officer report prints: families, cases, recipients or clients aided, dollars paid out and (from 1962) '
                   'reimbursed by the State, as printed. Wording and measure change by era (families aided to 1968, cases 1965-1982, monthly average recipients from FY2021) and are kept as printed. '
                   'Not the 1964 and 1971 tables (report-veterans-services.csv). Most editions print no count.'),
    'library-usage': ('Library usage: circulation, visits, volumes and hours, 1959-FY2025',
                   'What the Ritter Memorial Library and Lunenburg Public Library reports print about use: circulation (by section where printed, with totals; physical and electronic '
                   'counted separately in FY2025), visits, registered borrowers, volumes held and hours open. Wording, scope and rounding vary and are kept as printed; items in the 1960s-1970s '
                   'include periodicals, and later counts add videos and audio. Not the library service values table.'),
    'coa-services': ('Council on Aging service counts: Meals on Wheels and the senior van, 1976-FY2019',
                   'The counts the Council on Aging report prints for meals delivered to homebound elders and rides on the senior van, with the number of clients '
                   'where printed (FY2015-FY2019), and the Eagle House meal-site meals where the same page prints them (1996-1999). Counts only; clients are never named. '
                   'Wording and period vary (the year the page names to 1990, fiscal years from 1996, monthly averages in 1984, 1986 and 1987, one-way trips in 1996) and are kept as printed.'),
    'oneoff-finance': ('One-off finance tables worth keeping, 1962-FY2025',
                   'Single finance tables printed in one edition each: the 1958-62 five-year tax rate recap (1962), the county retirement assessment worked example (1981), '
                   'the FY2020 revenue by source and department changes (FY2019 report), the FY2024 undesignated fund balance roll-forward (marked unaudited) and '
                   'FY13-FY26 foundation enrolment with Chapter 70 aid (FY2025). Each table is its own row_group; the other editions print no such table in this family.'),
    'sped-indicators': ('Special education students served and state indicators, 1991-FY2025',
                   'What the Special Services reports say in sentences: students receiving special education and their share of the student population against the '
                   'state average, 504-plan counts, and from FY2013 the state indicators (graduation, dropout, suspension, parent involvement, MCAS index or scaled scores) '
                   'with the district figure, state rate and state target. Out-of-district placement counts are in placement-counts.csv; placement-mix '
                   'and compliance indicators are shares the page reports, not counts of children. Index scores (CPI) and scaled scores (SS) are different scales and are labelled as printed.'),
    'mcas-from-reports': ('School test results (MCAS) as the annual reports print them, 1998-FY2025',
                   'Lunenburg MCAS results as printed: the share of students at each performance level by grade and subject (1998-2005), '
                   'the share at the top levels against the state for the middle school and the high school (2006-FY2025), grade 3 Primary School results, '
                   'state rank and percentile where printed, and the FY2013 index scores for students with disabilities. Two different scales run through it: '
                   'Advanced / Proficient (to 2016) and Meeting / Exceeding Expectations (from 2017); they are not merged, and each row says which it is.'),
    'police-activity': ('Police Department activity counts by year, 1959-FY2025',
                   'The headline counts the Police Department printed each year: calls for service, incidents or complaints handled, arrests or court cases, '
                   'motor vehicle stops, accidents and protective custody, with the tabulation totals where the page ties its parts. The wording of the headline '
                   'count changes by era (miscellaneous calls, calls for service, incidents, incidents/calls) and is kept as printed, not merged.'),
    'town-nurse-visits': ('Town nurse visits and clinics, 1959-1976',
                   "The Town's own public health nurses' counts as the Health, Town Nurse and Town Nursing Service pages print them: nursing visits by kind, "
                   'Well Child Conferences, Well Oldster Clinics and immunization doses. Nashoba\'s own counts are in nashoba-public-health; each clinic row notes where the page credits both.'),
    'nashoba-public-health': ('Nashoba Associated Boards of Health services for Lunenburg, 1959-FY2025',
                   'The counts the annual reports print for what Nashoba did in Lunenburg: sanitation and environmental health inspections and tests, '
                   'septic and well work, nursing and home health visits, clinics, school dental programme, and (from 1963) communicable disease cases, '
                   'by disease where listed. Measures are kept as printed; renamed services are not merged. 2001-2007 are held in report-dept-activity.csv.'),
    'ballot-questions-local': ('Local ballot questions: votes by precinct, 1960-FY2025',
                   'Every question the Town put to its own voters that the annual reports print a tally for (debt exclusions, overrides, regional school, charter, '
                   'advisory questions, local acts and liquor licensing), with Yes, No and Blanks by precinct and the total the page prints. State questions and '
                   'candidates\' returns are not here; the four tallies already in ballot-questions.csv are listed as held elsewhere.'),
    'revolving-fund-limits': ('Revolving fund spending limits voted at town meeting, 1992-FY2025',
                   'The dollar limit town meeting voted on each revolving fund (fund, limit, and from FY2017 the spender, revenue source and purpose where the page prints them), '
                   'read from the town meeting articles in each report. These are voted limits, not spending; articles passed over are not rows.'),
    'receipts-fragments': ('Receipts and payments fragments, 1985 and FY2023',
                   'Pieces of the Treasurer\'s receipts and payments statements that the receipts and payments datasets lack: the 1985 receipts-list subtotals and total receipts, the 1985 Assessments group of payments, '
                   'and the FY2023 summary of receipts by category read from a 93 dpi page image. The FY2023 detail lines are not legible and are left out.'),
    'meeting-schedules-due-dates': ('Meeting schedules and tax due dates',
                   'The front-of-book list of when and where each board meets, 1960-FY2018, and the 1960-1963 list of when '
                   'real estate, excise and poll taxes and dog licences fall due, each as printed text. Boards that print their own regular meeting time on their report page are not rows.'),
    'fire-calls': ('Fire Department calls by year and category, 1959-FY2025',
                   'What the Fire Department printed about its calls in every annual report: the '
                   'total and each category as printed, with the quote and the PDF page. Parts '
                   'are tied to the printed total, and a year that does not tie says so.'),
    'tax-collection-holes': ('Tax collection by levy year: the editions the other two datasets do not hold',
                   'The Tax Collector\'s receivable table for 1961, 1962, 1967, FY2011-FY2013, FY2019 and '
                   'FY2024, by column and levy year, each column tied to the total the page prints.'),
    'monty-tech-budgets': ('Monty Tech budgets and assessments, 1998-FY2025',
                   'What the Montachusett Regional Vocational Technical School District printed in the annual reports about its own money: '
                   'the FY2017 report\'s financial pages (assessment on each of 18 member towns 1998-2017, FY2018 assessments by town, budget '
                   'build-up, ratio percentages, balance sheet) and the Educational Plan totals, grants and expense categories in the district\'s '
                   'reports to the towns, each tied to the total the page prints.'),
    'town-facts': ('Town facts that change: population, registered voters, road miles and area, 1959-FY2025',
                   'The measures on the About the Town / Lunenburg Profile page that change from year to year (population with its source kept apart: federal, state or '
                   'town census; registered voters; road miles; area), plus the census list on the school statistics page 1959-1973. Valuation and tax rate are held elsewhere.'),
    'cultural-council-grants': ('Cultural Council grants: applicant, project and amount, 1984-FY2024',
                   'What the local Cultural Council (earlier the Arts Lottery Council) printed about its grants: amounts named in the 1984-1985 reports, totals distributed 1986-1991 and FY2015, '
                   'the FY2016 account form, and applicant, project and amount lists for FY2016, FY2017, FY2018 and FY2021 (totals printed only for FY2016 and FY2018), with later totals and program counts.'),
    'sewer-billing': ('Sewer Commission: amount billed, delinquencies and connections, 2007-FY2025',
                   'What the Sewer Commission report printed about the sewer system: connection counts in a sentence for 2007-FY2011, then from FY2012 properties connected, properties with access not yet connected, '
                   'new accounts in the year, quarterly sewer bills billed out and delinquencies added to tax bills (billed and delinquent from FY2013).'),
    'capital-plan-holes': ('Capital plans: the editions capital-plans.csv does not hold',
                   'Capital plan items by department, item and amount for the May 2008, 2009, 2011, 2012, 2013 and 2023-2025 editions, '
                   'each list tied to the plan total the page prints, with the FY2013 and FY2024 lists the extractor refused read from the page image.'),
    'building-activity': ('Building permits issued by year, 1963-FY2025',
                   'What the Building Department (before 1975, the Zoning Authorities) printed about permits: applications received and permits issued by type with the printed totals for 1967-1982, '
                   'the sentence counts for 1986-2005, and the permits issued by type from FY2019 to FY2025 with the printed total. The definition of a permit changes (zoning permits to 1974, building permits only to 2005, then building, electrical, plumbing and gas together), so rows are only comparable within a run.'),
    'burials': ('Burials in the town cemeteries, by name, 1959-FY2025',
                   'The list of persons buried in the North and South Cemeteries that the Cemetery Commission (or Cemetery Department) report prints in every edition but FY2023: one row per person as printed, '
                   'with age, cemetery and month; 1959 to 1979 print age as years, months and days (1980 onward as one figure) and 1959 to 1968 print no cemetery. '
                   'Also the printed counts: full burials, cremations and totals (FY2018-FY2025), prose counts, and the DPW\'s "forty burials a year" average (2008-FY2021). Not the cemetery revenue lines in dollars.'),
    'pie-chart-shares': ('Revenue and spending pie charts, 1959-1968, 1983 and 1996-FY2023, and the 1930-1965 growth chart',
                   'The category and percent printed on the town\'s pie charts: Where Did Your Tax Dollar Go (cents per dollar, 1959-1967; percents, 1968), We Received and We Spent (1959-1968), the FY 1983 expenditures pie, and General Fund revenues and expenditures (1996-FY2023, no revenues pie in 2005 or FY2019), '
                   'plus the 1965 chart of tax rate, valuation and population at each five-year point 1930-1965. Percents are as printed, never computed; the legend percents beside the 1960-1967 and 1983 pies are in report-expenditure-shares.csv and are not repeated. '
                   'Three small slices of the 1959 payments pie were too small to read and are left out.'),
    'official-lists': ('Other named lists of officials, 1959-FY2025',
                   'Name and rank or role as printed for people on lists town-roster-entries.csv and staff-roster-entries.csv do not hold: the Fire Department company rosters of 1964-1968, the 1985 fire history, committee, commission and board lists and signature blocks, '
                   'school central-office and Montachusett administration lists, and the 1969 Montachusett district committee by town. Only lines where the role ends the printed line are read; a name inside a sentence is not a row.'),
    'staff-roster-pages': ('School staff rosters: pages the staff-roster-entries reader did not load',
                   'Named school staff and councils on pages staff-roster-entries does not hold: the 1964 new-teacher '
                   'table and statistics cells, the 1976 personnel listing (names), 1985 teaching-staff pages 150 and 156 '
                   '(names), the LHS School Council lists 1993-1995, and the school-council lists and staffing counts '
                   'on the Passios and Primary School pages of 2001 and 2005-2007. The rest is in staff-roster-entries.csv.'),
    'treasurer-cash-investments': ("Treasurer's cash investments, 1977-FY1981",
                   'The Treasurer\'s Recapitulation of Revenue Cash Invested in the 1978, 1979 and 1980 reports: by half year, each bank and vehicle line with its number of instruments, liquidity, denominations, rate range, total invested and interest earned, '
                   'the half-year, fiscal-year and calendar-year totals and the interest received and to-be-received reconciliation; the 1977 weekly cash flow worksheet for February 1978 (columns that are whole on the page); and the 1977 table of Town Office cost, interest paid and interest earned, 1970-FY1979. All read from page images.'),
}


def catalogue_items():
    """(path, title, stars, description) for build_source_index.py, one family at a time."""
    items = [('data/series-coverage.csv', 'Which annual reports were checked for each series', 1,
              'One row per series per edition: whether the series is printed there and, if not, '
              'which pages were looked at.')]
    for family, (title, what) in sorted(FAMILIES.items()):
        items += [('data/series-%s.csv' % family, title, 2, what),
                  ('data/report-series/%s.csv' % family, title + ': the read', 1,
                   'Written by us. The read itself, before the checks in report_series.py add '
                   'their columns.'),
                  ('data/report-series/%s.coverage.csv' % family, title + ': editions looked at', 1,
                   'Written by us. Every edition, and whether the series is printed there.')]
    return items


def normalise(s):
    """Letters and digits only, so line wraps, column gaps and OCR punctuation do not matter."""
    s = re.sub(r'(?m)^\s*\d+\|', ' ', s)     # the budget page files number their lines
    s = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', s)  # a word hyphenated across a line
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def editions():
    """edition label -> every text layer we hold for it."""
    out = {}
    for path in sorted(glob.glob(os.path.join(TEXT, '*.txt'))):
        m = re.search(r'-fy-(\d{4})-annual', path)
        if m:
            out.setdefault('FY' + m.group(1), []).append(path)
            continue
        m = re.search(r'-(\d{4})-annual', path) or re.search(r'(\d{4}) Annual', path)
        if m:
            out.setdefault(m.group(1), []).append(path)
    for path in sorted(glob.glob(os.path.join(BUDGET_PAGES, 'FY*.txt'))):
        out.setdefault(os.path.basename(path)[:6], []).append(path)
    return out


_cache = {}


def pages_of(path):
    if path not in _cache:
        with open(path, errors='replace') as f:
            parts = re.split(r'===PAGE (\d+)===[^\n]*\n?', f.read())
        _cache[path] = {int(parts[i]): normalise(parts[i + 1]) for i in range(1, len(parts), 2)}
    return _cache[path]


def quote_on_page(quote, edition, page_field, eds):
    """Is the quote on this page? A row may cite a span, `14-15`, when a list crosses a page."""
    n = normalise(quote)
    pages = [int(p) for p in re.findall(r'\d+', page_field)]
    if len(pages) == 2:
        pages = list(range(pages[0], pages[1] + 1))
    joined = ''
    for path in eds.get(edition, []):
        got = pages_of(path)
        text = ' '.join(got.get(p, '') for p in pages)
        if n and n in text:
            return True
        joined += ' ' + text
    # A two-column page reads label and figure apart: both must still be on the page.
    words = n.split()
    return bool(words) and all(re.search(r'\b%s\b' % re.escape(w), joined) for w in words) and 'apart'


def read_family(path, eds, problems):
    family = os.path.basename(path)[:-4]
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != READ_COLS:
            problems.append('%s: columns are %s' % (family, reader.fieldnames))
            return family, []
        rows = list(reader)
    groups = {}
    for i, r in enumerate(rows, 2):
        where = '%s line %d (%s p%s)' % (family, i, r['edition'], r['pdf_page'])
        if r['row_role'] not in ROLES:
            problems.append('%s: role %r' % (where, r['row_role']))
        if r['edition'] not in eds:
            problems.append('%s: no such edition' % where)
        found = quote_on_page(r['quote'], r['edition'], r['pdf_page'], eds)
        r['quote_found'] = 'apart' if found == 'apart' else 'yes' if found else 'no'
        if r['quote_found'] == 'no':
            problems.append('%s: quote not on the page: %r' % (where, r['quote'][:70]))
        if r['year'].startswith('FY'):                    # `year` compares as a number; the basis keeps the kind
            r['year'] = r['year'][2:]
            if 'fiscal' not in r['year_basis']:
                r['year_basis'] = 'fiscal'
        if not re.fullmatch(r'\d{4}', r['year']):
            problems.append('%s: year %r' % (where, r['year']))
        digits = r['value'].replace(',', '').lstrip('-')  # a printed (25,900) is read as -25900
        if re.fullmatch(r'-?[\d,]*\.?\d+', r['value']):
            r['value'] = r['value'].replace(',', '')      # so a column of figures sums in SQL
        if digits and 'spelled' not in r['note'] and 'misread' not in r['note'] \
                and not re.search(r'(?<![\d.])%s(?![\d])' % re.escape(digits),
                                  r['quote'].replace(',', '')):
            problems.append('%s: value %s is not in its quote' % (where, r['value']))
        groups.setdefault((r['year'], r['edition'], r['row_group']), []).append(r)
    for rs in groups.values():
        total = [r for r in rs if r['row_role'] == 'total']
        parts = [float(r['value'].replace(',', '')) for r in rs if r['row_role'] == 'part' and r['value']]
        printed = float(total[0]['value'].replace(',', '')) if total else None
        psum = sum(parts) if parts else None
        ties = 'no total printed' if printed is None else 'no parts printed' if psum is None else \
            'yes' if abs(printed - psum) < TIES_TOLERANCE else 'no, parts %+g against the total' % (psum - printed)
        for r in rs:
            r['group_parts_sum'] = '' if psum is None else '%g' % psum
            r['group_total_printed'] = '' if printed is None else '%g' % printed
            r['group_ties'] = ties
    return family, rows


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def build(eds, problems):
    outputs, coverage = {}, []
    for path in sorted(glob.glob(os.path.join(READS, '*.csv'))):
        if path.endswith('.coverage.csv'):
            continue
        family, rows = read_family(path, eds, problems)
        if family not in FAMILIES:
            problems.append('%s: add it to FAMILIES, or the catalogue cannot describe it' % family)
        outputs[os.path.join(DATA, 'series-%s.csv' % family)] = csv_text(OUT_COLS, rows)
        cov_path = path[:-4] + '.coverage.csv'
        if not os.path.exists(cov_path):
            problems.append('%s: no coverage file; every edition must be accounted for' % family)
            continue
        with open(cov_path, newline='') as f:
            cov = {c['edition']: c for c in csv.DictReader(f)}
        held = {r['edition'] for r in rows}
        for ed in sorted(eds):
            c = cov.get(ed)
            if c is None:
                problems.append('%s: edition %s was not looked at' % (family, ed))
                continue
            if (c['status'] == 'held') != (ed in held):
                problems.append('%s: edition %s says %r, and holds %s rows'
                                % (family, ed, c['status'], 'some' if ed in held else 'no'))
            if c['status'] != 'held' and not c['pages_looked'].strip():
                problems.append('%s: edition %s says %r but names no page looked at'
                                % (family, ed, c['status']))
            coverage.append(dict(c, family=family))
    outputs[os.path.join(DATA, 'series-coverage.csv')] = csv_text(COVERAGE_COLS, coverage)
    return outputs


def raw_pages(path):
    with open(path, errors='replace') as f:
        parts = re.split(r'===PAGE (\d+)===[^\n]*\n?', f.read())
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def find(pattern):
    """A survey tool. A search that finds nothing is a fact about this search (rule 13c)."""
    rx, eds = re.compile(pattern, re.I), editions()
    for ed in sorted(eds):
        seen, hits = set(), 0
        for path in eds[ed]:
            for page, text in sorted(raw_pages(path).items()):
                for line in text.split('\n'):
                    line = re.sub(r'^\s*\d+\|', '', line).strip()
                    if rx.search(line) and (page, line) not in seen:
                        seen.add((page, line))
                        hits += 1
                        if hits <= 12:
                            print('%s p%d: %s' % (ed, page, line[:130]))
        print('== %s: %d line(s)' % (ed, hits))
    return 0


def show_page(edition, page):
    for path in editions().get(edition, []):
        print('--- %s' % os.path.basename(path))
        print(raw_pages(path).get(page, '(no such page in this layer)'))
    return 0


def main():
    if '--find' in sys.argv:
        return find(sys.argv[sys.argv.index('--find') + 1])
    if '--page' in sys.argv:
        i = sys.argv.index('--page')
        return show_page(sys.argv[i + 1], int(sys.argv[i + 2]))
    check = '--check' in sys.argv
    eds, problems = editions(), []
    outputs = build(eds, problems)
    if check:
        for path, text in outputs.items():
            old = open(path).read() if os.path.exists(path) else None
            if old != text:
                problems.append('%s is stale' % os.path.relpath(path, ROOT))
    for p in problems:
        print('FAIL', p)
    if problems:
        return 1
    if not check:
        for path, text in outputs.items():
            with open(path + '.tmp', 'w') as f:
                f.write(text)
            os.replace(path + '.tmp', path)
    for path, text in sorted(outputs.items()):
        print('%s %s: %d rows' % ('ok' if check else 'wrote', os.path.relpath(path, ROOT), text.count('\n') - 1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
