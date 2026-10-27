"""Which of the three town mirrors a document belongs in.

`sources/` splits the town's document store three ways, because a folder called budget
should hold budgets:

    town-budget/          budgets, presentations, warrants, financial statements,
                          capital plans — data, spreadsheets and plans
    town-supplementary/   tax billing and exemptions, the senior work-off programme,
                          police policies, HR forms, grant notices, infrastructure
    town-annual-reports/  the annual town report, one per year

**This lives in one file because two copies of a classification rule drift.** The fetcher
routes new documents with it and any repair re-derives the split with it, so the two cannot
disagree — which they did, four times, when the fetcher wrote everything to `town-budget/`
and a later pass moved it out again.

Classified from the label the town gives a document, which is the only thing available at
fetch time — the bytes have not been read yet and often cannot be.
"""
import re

from report_year import report_year

FOLDERS = ('town-budget', 'town-supplementary', 'town-annual-reports')

# WIDENED 27 October 2026, for the reports back to the 1980s the Select Board chair is
# uploading. The town titled those by YEAR -- `Town Report 1985`, `Town Report 2000` -- and
# the old pattern wanted the words `annual town report`, so they would have been filed as
# supplementary. `town report` is enough when the label also names one year; on its own it
# is too loose to trust. (`Town Manager Report` does not match: the words are not adjacent.)
ANNUAL = re.compile(r'annual town report', re.I)
TOWN_REPORT = re.compile(r'\btown reports?\b', re.I)

# Widened 5 September after the ArchiveCenter crawl, which is where the town's RETIRED
# budget material lives -- FY12 to FY25. Fifteen documents classified as supplementary that
# are plainly budget: revenue-expense worksheets, five-year financial forecasts, line-item
# detail, capital plan presentations, the FY2013 budget appendices, and the budget symposium
# decks. None of them contains the word "budget".
BUDGET = re.compile(
    r'budget|operating budget|year.?end report|financial statement|capital|'
    r'warrant|town meeting|monty tech|proposition 2\.5|preliminary budget|'
    r'hiring plan|overtime costing|detail rates|goals|roadway capital|'
    r'revenue.?expense|financial forecast|forecast presentation|line item|'
    r'cap plan|projected identified needs|symposium|appendix document', re.I)

# Labels that carry a budget word and are not budget documents. Without these, a police
# policy on 'Reserve Officer Hiring' and a W-4 land in town-budget/ on the word alone.
NOT_BUDGET = re.compile(
    r'w-4|conflict of interest|bencor|sex offender|code of conduct|'
    r'snow and ice|resource officer|reserve officer', re.I)


def is_annual_report(label, category=''):
    """True for the annual town report, by its label or by where the town filed it.

    `category` is the shelf the document came off: the ArchiveCenter category, or the
    DocumentCenter page that linked it. The town's own `Annual Town Reports` shelf is a
    stronger statement than any label it writes, so a report it files there is a report
    whatever it is called.
    """
    if ANNUAL.search(label) or ANNUAL.search(category or ''):
        return True
    return bool(TOWN_REPORT.search(label) and report_year(label))


def home(label, category=''):
    """The folder a document with this label belongs in."""
    if is_annual_report(label, category):
        return 'town-annual-reports'
    if BUDGET.search(label) and not NOT_BUDGET.search(label):
        return 'town-budget'
    return 'town-supplementary'
