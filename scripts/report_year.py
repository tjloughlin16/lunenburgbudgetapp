"""Which year a town document's LABEL names, and whether the label calls it fiscal or calendar.

    from report_year import report_year
    report_year('FY85 Annual Town Report (PDF)')   # Year(1985, 'fiscal', 'FY85')
    report_year('Town Report 2000')                # Year(2000, 'calendar', '2000')

One parser, because there were three and they disagreed. `fetch_town_docs.dedupe_key()`
turned `FY85` into `fy2085`; `report_pages.py` and `map_annual_report_pages.py` wanted
`fy-YYYY` in a filename and crashed or skipped without it; and nothing at all read `Town
Report 2000`, which is how the town titled reports before it titled them by fiscal year.

THE TWO-DIGIT RULE, STATED: `FY` + two digits is 19xx when the digits are PIVOT or above,
20xx below it. So FY85 is 1985 and FY25 is 2025. Lunenburg's reports go back to the 1980s
and forward to now; a pivot of 50 leaves both ends a quarter-century of room.

WHAT `basis` MEANS, AND WHAT IT DOES NOT. It is what the LABEL says:

    fiscal     the label writes FY, or names a span of two consecutive years
               (`1999-2000`), which is how a fiscal year is written in words.
               A span is the fiscal year it ENDS in: July 1999 to June 2000 is FY2000.
    calendar   the label names a plain year and nothing else.

A plain year on a label is not proof the report covers January to December -- only the
cover says that ("for the year ending December 31"). `calendar` is the label's claim, read
literally, and anything that matters downstream should check the cover.

A label with no year, or with two years that are not one fiscal span (`FY24-FY33 Capital
Plan`), returns None. A plan covering ten years is not a report for one of them, and
guessing which would file it under the wrong year.
"""
import collections
import re

PIVOT = 50

Year = collections.namedtuple('Year', 'year basis matched')

FY = re.compile(r'\bFY\s*[-.]?\s*(\d{4}|\d{2})(?!\d)', re.I)
SPAN = re.compile(r'\b((?:19|20)\d{2})\s*[-/–]\s*((?:19|20)?\d{2})(?!\d)')
PLAIN = re.compile(r'(?<![\d.])((?:19|20)\d{2})(?![\d.])')


def four(digits):
    """FY two digits to a year, by the stated pivot."""
    n = int(digits)
    if len(digits) == 4:
        return n
    return (1900 if n >= PIVOT else 2000) + n


def report_year(label):
    """Year(year, basis, matched) for the one year a label names, or None."""
    label = label or ''
    fys = FY.findall(label)
    if fys:
        years = {four(d) for d in fys}
        if len(years) != 1:
            return None
        m = FY.search(label)
        return Year(years.pop(), 'fiscal', m.group(0))
    m = SPAN.search(label)
    if m:
        a, b = int(m.group(1)), m.group(2)
        b = int(b) if len(b) == 4 else (a // 100) * 100 + int(b)
        if b <= a and len(m.group(2)) == 2:      # 1999-00 crosses the century
            b += 100
        if b == a + 1:
            return Year(b, 'fiscal', m.group(0))
        return None
    years = {int(y) for y in PLAIN.findall(label)}
    if len(years) == 1:
        y = years.pop()
        return Year(y, 'calendar', str(y))
    return None


# THE FILENAME HALF. Two shapes of annual report are held under town-annual-reports/docs/:
#
#   4130-fy-2025-annual-town-report.pdf    FY2011-FY2025, read on Vision and proven
#   4526-2000-annual-town-report.pdf       1959-2010, fetched 28 October 2026, read on Textract
#
# The leading number is the town's DocumentCenter id and is NOT a year -- `report_year()` on
# the whole name would read `2003-2004-...` as the span FY2004 -- so it is stripped first.
# `basis` is the label's claim, as above: a calendar edition's balance sheet may still be
# for a fiscal year (the 2000 report's is "FOR THE YEAR ENDED JUNE 30, 2000"); check the page.
Edition = collections.namedtuple('Edition', 'key year basis')
FY_FILE = re.compile(r'fy-?(\d{4})')
CALENDAR_FILE = re.compile(r'^\d+-((?:19|20)\d{2})-annual-town-report')


def report_edition(name):
    """Edition('FY2011', 2011, 'fiscal') | Edition('2000', 2000, 'calendar') | None, from a filename."""
    import os
    base = os.path.basename(name)
    add = '-addendum' if 'addendum' in base else ''
    m = FY_FILE.search(base)
    if m:
        return Edition('FY%s%s' % (m.group(1), add), int(m.group(1)), 'fiscal')
    m = CALENDAR_FILE.match(base)
    if m:
        return Edition('%s%s' % (m.group(1), add), int(m.group(1)), 'calendar')
    return None


def fiscal_editions(paths):
    """Only the FY-named reports. THE VISION-ERA EXTRACTORS READ THESE AND NOTHING ELSE: their
    layouts, reprints and page reads are written per fiscal year, and a 1960s report handed to
    them would produce `FYNone` rows or crash. A calendar edition reaches them only once it has
    its own page map (notes/PLAN-ANNUAL-REPORT-PIPELINE.md, P4)."""
    import os
    return [p for p in paths if FY_FILE.search(os.path.basename(p))]
