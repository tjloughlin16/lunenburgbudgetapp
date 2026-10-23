"""WHAT COUNTS AS SPECIAL EDUCATION, IN ONE PLACE: the items where DESE's word decides.

    import sped_definition as SD
    SD.ITEMS                 # every row of sources/data/sped-definition.csv
    SD.ADDED_ACCOUNTS        # ledger accounts counted although no label says special education
    SD.EXCLUDED_ACCOUNTS     # ledger accounts left out although a label or segment 51 says it
    SD.EXCLUDED_FUNCTIONS    # function codes no rule counts in a total
    SD.EXCLUDED_LINE_ITEMS   # budget book lines left out
    SD.LABELS                # extra spellings the budget model reads as special education

TJ, 23 October 2026: "if those match DESE then we need to include them". The site measures
special education three ways -- budget lines (model/sped.py), the ledger's labels
(scripts/journal.py) and the ledger's segment 51 (scripts/build_sped_costs.py) -- and each
read the account names its own way, so they disagreed with DESE and with each other on the
same handful of items. Those items are decided ONCE, in `sources/data/sped-definition.csv`,
each with the DESE document and cell that decides it, and all three rules read them from
here. A rule that wanted to differ would have to stop importing this module, which is the
point.

The CSV is the source of truth; this module only parses it, and refuses a row it cannot
place. /special-education/sped-definition (scripts/build_sped_crosswalk.py) renders it and
checks every report cell it cites against what the cell holds.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, 'sources', 'data', 'sped-definition.csv')
COLS = ['id', 'item', 'decision', 'accounts', 'functions', 'line_items', 'labels', 'dese_rule',
        'dese_citation', 'report_cells', 'why']
DECISIONS = ('counted', 'not counted')


def _split(s):
    return tuple(x.strip() for x in (s or '').split(';') if x.strip())


def _load():
    with open(CSV_PATH, encoding='utf-8', newline='') as fh:
        r = csv.DictReader(fh)
        if r.fieldnames != COLS:
            raise SystemExit('sped_definition: %s has columns %s, not %s'
                             % (CSV_PATH, r.fieldnames, COLS))
        rows = list(r)
    seen = set()
    for row in rows:
        if row['id'] in seen:
            raise SystemExit('sped_definition: id %r appears twice' % row['id'])
        seen.add(row['id'])
        if row['decision'] not in DECISIONS:
            raise SystemExit('sped_definition: %s has decision %r' % (row['id'], row['decision']))
        if not row['dese_citation'].strip():
            raise SystemExit('sped_definition: %s cites no DESE document' % row['id'])
        for k in ('accounts', 'functions', 'line_items', 'labels'):
            row[k] = _split(row[k])
        row['report_cells'] = _split(row['report_cells'])
        if row['decision'] == 'counted' and row['functions']:
            raise SystemExit('sped_definition: %s would count a whole function; name the '
                             'accounts' % row['id'])
    return rows


ITEMS = _load()
ADDED_ACCOUNTS = {a: r['id'] for r in ITEMS if r['decision'] == 'counted' for a in r['accounts']}
EXCLUDED_ACCOUNTS = {a: r['id'] for r in ITEMS if r['decision'] == 'not counted'
                     for a in r['accounts']}
EXCLUDED_FUNCTIONS = {f: r['id'] for r in ITEMS if r['decision'] == 'not counted'
                      for f in r['functions']}
EXCLUDED_LINE_ITEMS = {x: r['id'] for r in ITEMS if r['decision'] == 'not counted'
                       for x in r['line_items']}
LABELS = tuple(lab for r in ITEMS if r['decision'] == 'counted' for lab in r['labels'])
if set(ADDED_ACCOUNTS) & set(EXCLUDED_ACCOUNTS):
    raise SystemExit('sped_definition: an account is both counted and not counted')


def function_of(account):
    """Segment 4 of a nine-segment account string."""
    return account.split('-')[3]


def ledger_scope(account):
    """'added', 'excluded' or None: what this list says about one ledger account."""
    if account in EXCLUDED_ACCOUNTS or function_of(account) in EXCLUDED_FUNCTIONS:
        return 'excluded'
    if account in ADDED_ACCOUNTS:
        return 'added'
    return None


def item_of(account):
    """The registry row that decides a ledger account, or None."""
    rid = (EXCLUDED_ACCOUNTS.get(account) or EXCLUDED_FUNCTIONS.get(function_of(account))
           or ADDED_ACCOUNTS.get(account))
    return rid
