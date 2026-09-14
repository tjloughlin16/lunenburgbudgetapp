"""The town's budget DECISION cycles: the season that builds FY(n) opens the day after the
annual town election of year n-2 and closes on the election of year n-1 -- not on 30 June.

TJ, 14 September 2026: "the FY for the town and budget goes through town meeting and
election. so all decisions are final after that. That's the new FY."

Read from sources/data/budget-cycles.csv, whose dates are the election days printed in the
annual town reports (and, for 2026, the posted results). The live cycle has no close yet.
"""
import csv
import datetime as dt
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYCLES = os.path.join(ROOT, 'sources', 'data', 'budget-cycles.csv')


def cycles():
    rows = list(csv.DictReader(open(CYCLES, encoding='utf-8')))
    return sorted((dict(r, fy=int(r['fy'])) for r in rows), key=lambda r: r['fy'])


def cycle_for(date):
    """The cycle a date falls in. Before the table starts, or in a year the table lacks,
    fall back to the election-in-May convention: after 20 May counts as the next season."""
    for c in cycles():
        if c['opens'] and date < c['opens']:
            continue
        if not c['closes'] or date <= c['closes']:
            if not c['opens'] or date >= c['opens']:
                return c
    d = dt.date.fromisoformat(date)
    fy = d.year + 1 + (1 if (d.month, d.day) > (5, 20) else 0)
    return dict(fy=fy, opens='', closes='', election='', source='convention', note='no election date held for this year')


def fy_of(date):
    return cycle_for(date)['fy']


def span(fy):
    """(opens, closes) for a cycle; closes is '' while the season is under way."""
    for c in cycles():
        if c['fy'] == fy:
            return c['opens'], c['closes']
    return '', ''
