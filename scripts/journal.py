#!/usr/bin/env python3
"""THE SCHOOL MUNIS JOURNAL, SHARED: one loader, one set of definitions, every report reads it.

    import journal as J
    lines = J.lines()                     # every journal line, amount as Decimal, fy as int
    acct = J.accounts()                   # account -> its row, with the FY2026 printed figures
    J.is_sped(acct['0100-...'])           # THE special education account list (below)

    python3 scripts/journal.py            # print the definitions as applied: how many accounts
                                          #   each class and component holds, and the payees
                                          #   the normaliser merges -- for a person to read

WHY ONE MODULE. notes/plans/MUNIS-JOURNAL-REPORTS.md: "Every generator imports it. A second
copy of any of these is a defect." Five reports on two shelves read the same 49,000 lines, and
each needs the same four decisions -- which source code is an actual, which accounts are
special education, which fund is which, and when two payee names are one payee. Made once
here, they cannot be made two ways.

THE DATA. `sources/data/munis-school-journal.csv` (one row per journal line) and
`munis-school-journal-accounts.csv` (one row per account), our redacted reading of the
Town's Report 1, written by `scripts/extract_munis_school_journal.py`. Read from the CSVs,
never from `lunenburg.db`: the CSVs are the source of truth and the database is derived from
them (notes/reference/SCHEMA.md).

WHAT A LINE IS (rule 11). Every amount is a posting to a SCHOOL account. A line is not what a
thing costs: benefits charged outside the school department, and anything a grant paid that
was never posted to a school account, are not here. An all-funds view narrows the gap the
general fund leaves; it does not close it.

THE FY2026 CLOSE IS NOT IN THIS RUN. Encumbrances were still open when the Town ran the
report (`OPEN_FY`), so an FY2026 actual can still move. Every report that shows FY2026 says so.

=== WHAT "SPENT" MEANS ON THIS SITE ===

TJ, 23 October 2026, deciding it for every page: "'spent' - payments plus owed." Wherever school
spending is shown as SPENT against a budget or a vote, it is the year's actuals (`COLUMN_OF` ->
'actual': invoices paid, pay runs, journal entries, receipts) PLUS what was still owed at the
year end (-> 'encumbrance'). `SPENT` names the two columns and `is_spent()` applies them; a
report that compares spending with a budget reads one of those, never 'actual' alone.

What that comes to, measured, so nobody has to rediscover it: in a CLOSED year the close
(`YEC`) zeroes the year's encumbrances and the next year re-opens them (`SOY`), so a closed
year's encumbrance column nets to nothing and its spent equals its payments; what was owed at
that close is counted in the year it was paid. Only the open year (`OPEN_FY`) carries an
encumbrance, and that is what the definition adds. The same holds for the period-13
spreadsheets, whose `encumbrances` column is zero in every closed year.

Two things are NOT spent and keep the actual column: a fund BALANCE (cash: what came in less
what was paid -- an order not yet paid has not left the fund), and any tie to a document that
prints actuals (the period-13 `ytd_expended`, the annual town report's disbursements, DESE's
End of Year report). A tie compares like with like, whatever the page presents.

=== THE FOUR DEFINITIONS ===

1. SOURCE CODES -> the column of the printed report they post to (`COLUMN_OF`). Proven, not
   assumed: it is the only assignment under which all 3,356 accounts close to the cent
   against the figures the report prints (the extractor's tie 1). `GEL` is an encumbrance --
   it was first put with the actuals and one account failed by $258.72. The extractor imports
   this table from here, so the `posts_to` column of the CSV and every report agree by
   construction. `KIND_OF` splits the actuals by what produced them: an invoice paid, a pay
   run, a journal entry, a receipt.

2. THE SPECIAL EDUCATION ACCOUNT LIST (`SPED_ACCOUNTS`), matched on an account's description,
   its org name and its fund name together. ONE DEFINITION, TWO USES:
     * the extractor's redaction: a transportation payee on one of these accounts is a special
       education family and stays masked (TJ, 19 October 2026: "As long as its not SPECIAL
       EDUCATION");
     * every special education cost report.
   It lives here, and the extractor imports it, so the accounts a report counts as special
   education are exactly the accounts whose families the published CSV masks. A report that
   widened the list without the redaction would publish payees the redaction thought were not
   special education; this makes that impossible rather than unlikely.

   The redaction errs wide on purpose, and one part of the list is wider than a cost report
   should count: SCHOOL PSYCHOLOGISTS (`PSYCH` matches them). Psychologists serve every
   student, and their salary accounts are not special education accounts by any label the
   Town gives them. So they are IN the list -- masked as special education, which is the
   cautious direction -- and their component is declared `in_total=False` (`COMPONENTS`):
   reports show them beside the special education total, never inside it. That is OUR
   choice, named here and on every page that uses it.

   NOT in the list, and so in no special education figure: `D.W. SPECIALISTS` (district-wide
   specialists, org S2510061), the guidance counsellors and social workers, the nurses, and
   any special education work paid from an account with no special education label. The list
   is what the ledger LABELS special education. What it spends on children with a plan in
   general education accounts is not separable here.

3. FUNDS (`sped_fund`): the general fund (0100), the circuit breaker (2640, the state's
   reimbursement account), the IDEA grants (DESE grant codes 240 and 262, and the two ARP
   IDEA grants, 252 and 264, and ARRA's 760 and 762), other special education grants (274 and
   298, the program improvement grants; 242), and two school revolving funds that sit on the
   list and have never posted a line in this run. Read off the fund NUMBER and the grant code in its name, not off
   free text.

4. PAYEES (`payee`). A shown payee is the name the extractor kept, normalised by `vendor_key`:
   case, spacing and trailing punctuation only (`SCHOLASTIC INC.` = `SCHOLASTIC INC`), plus
   `ALIASES`, declared one at a time with the evidence (FLLAC = Keystone, so a page names the
   collaborative by the program name the town's meetings use). A vendor number is NOT the key: the
   Town holds some vendors under two numbers (`002025` and `2025`) and the same name is the
   same payee. A MASKED payee -- a family or child the redaction hid -- has no key at all and
   is never normalised, merged, counted or split: `payee()` returns `MASKED`, and reports may
   only add masked lines into an aggregate that also holds other payees (`masked_ok`).
"""
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
JOURNAL_CSV = os.path.join(DATA, 'munis-school-journal.csv')
ACCOUNTS_CSV = os.path.join(DATA, 'munis-school-journal-accounts.csv')
YEARS = (2023, 2024, 2025, 2026)
OPEN_FY = 2026          # the year whose close is not posted in this run

# The public addresses of the data, for a page's sources.
PUBLIC = {'journal': '/docs/data/munis-school-journal.csv',
          'accounts': '/docs/data/munis-school-journal-accounts.csv',
          'image_pages': '/docs/data/munis-school-journal-image-pages.csv'}

# ---------------------------------------------------------------- 1. source codes

COLUMN_OF = {'BUC': 'original_budget', 'BUA': 'transfer'}
COLUMN_OF.update({s: 'actual' for s in ('API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP')})
COLUMN_OF.update({s: 'encumbrance' for s in ('POE', 'POL', 'POM', 'SOY', 'YEC', 'GEL')})
CLASSES = ('actual', 'encumbrance', 'original_budget', 'transfer')
# THE SITE'S DEFINITION OF SPENT (module docstring): payments plus what is still owed.
SPENT = ('actual', 'encumbrance')


def is_spent(r):
    """A line that counts as spent: an actual, or an encumbrance still owed."""
    return r['posts_to'] in SPENT

# What produced an ACTUAL. Read off the codes as the lines use them: API/APM carry a vendor and
# an invoice; PRJ/PRH carry a payroll warrant and no person (see `PAYROLL_GRAIN`); GEN/GRV are
# journal entries and their reversals ("RECLASS", "YE ENTRY", "REVERSE"); CRP is a cash
# receipt credited against an expense (a refund, a worker's compensation receipt).
KIND_OF = {'API': 'invoice', 'APM': 'invoice', 'PRJ': 'payroll', 'PRH': 'payroll',
           'GEN': 'journal entry', 'GRV': 'journal entry', 'CRP': 'receipt'}

# MEASURED 19 October 2026 (the plan's first settle-first question): a PRJ line is one line per
# ACCOUNT per payroll warrant -- never per person. Every PRJ line has an empty vendor, an
# empty invoice and a `WARRANT=<n>P<yy> RUN=1` description, and no account carries two PRJ
# lines in one journal. Payroll dollars are not people (rule 7): a line is what a pay run cost
# an account, however many people it paid.
PAYROLL_GRAIN = 'one line per account per payroll warrant; no person is recorded'

# ---------------------------------------------------------------- 2. special education

SPED_ACCOUNTS = re.compile(r"SPED|SPEC(?:IAL)?\.? ED|CIRCUIT BREAKER|\bIDEA\b|\b240\b|\b262\b"
                           r"|TUITION|\bPLACEM|\bOOD\b|OUT OF DIST|RELATED SERVICES|EVALUATION"
                           r"|TUTOR|THERAP|PSYCH|COLLABORATIVE", re.I)


def account_text(a):
    """What SPED_ACCOUNTS is matched against: description, org name and fund name."""
    return ' | '.join([a['account_description'], a['org_name'], a['fund_name']])


def is_sped(a):
    """On THE special education list -- the redaction's scope and every report's."""
    return bool(SPED_ACCOUNTS.search(account_text(a)))


def is_expense(a):
    return a['object'].startswith('5')


def is_revenue(a):
    return a['object'].startswith('4')


# THE COMPONENTS of special education spending, by object code. Every expense account on the
# list must land in exactly one, or `component()` refuses: a new object code is a decision.
#   (id, label, in_total, object codes)
COMPONENTS = [
    ('tuition', 'Out-of-district tuition', True, ('535019', '535022', '535023')),
    ('transport', 'Transportation', True, ('535026',)),
    ('contracted', 'Contracted services and evaluations', True,
     ('519016', '531006', '531067', '535004', '535006', '535007', '535011', '535012',
      '535013')),
    ('pay', 'Staff pay and benefits', True,
     ('511001', '511002', '511003', '511025', '511103', '511203', '512103', '512203',
      '517000', '517001', '519005', '519015', '519996', '519997', '519998', '519999',
      '570001')),
    ('supplies', 'Supplies, equipment and other', True,
     ('525007', '540000', '545001', '555007', '555050', '555055', '575001', '575002',
      '575003', '575004', '575005', '585001')),
    # OUR CHOICE, see the module docstring: on the list, outside the total.
    ('psychologists', 'School psychologists', False, ('511023',)),
    # On the list only because the word TUITION is in the account name: school choice and
    # charter tuition, and course reimbursement. Not special education. No line has ever
    # posted to them in this run; if one does, it is shown beside the total, never in it.
    ('not-sped', 'Not special education (named tuition)', False, ('535027', '535028', '535029')),
]
_COMPONENT_OF = {o: c for c, _, _, objs in COMPONENTS for o in objs}
COMPONENT_LABEL = {c: l for c, l, _, _ in COMPONENTS}
IN_TOTAL = {c for c, _, t, _ in COMPONENTS if t}


def component(a):
    if not (is_sped(a) and is_expense(a)):
        return None
    c = _COMPONENT_OF.get(a['object'])
    if c is None:
        raise SystemExit('journal.py: special education account %s has object %s (%s), which no '
                         'component holds -- declare it in COMPONENTS'
                         % (a['account'], a['object'], a['account_description']))
    return c


def in_sped_total(a):
    c = component(a)
    return c is not None and c in IN_TOTAL


# ---------------------------------------------------------------- 3. funds

SPED_FUNDS = ('General fund', 'Circuit breaker', 'IDEA grants', 'Other special education grants',
              'School revolving funds')
# DESE grant codes. 240 and 262 are the IDEA entitlement and early childhood grants; 252 and
# 264 the ARP IDEA grants; 760 and 762 the ARRA IDEA grants of FY2010-FY2011. 274 and 298 are
# program improvement grants, and 242 the electronic portfolio grant of FY2005-FY2006.
IDEA_CODES = ('240', '262', '252', '264', '760', '762')
OTHER_SPED_CODES = ('274', '298', '242')
REVOLVING = ('1303', '1307')     # summer school, non-resident tuition: on the list, never used


def grant_code(fund_name):
    m = re.search(r'#\s*(\d{3})\b', fund_name)
    return m.group(1) if m else None


def sped_fund(a):
    """Which of SPED_FUNDS an account on the list posts to. Refuses an account it cannot place."""
    if a['fund'] == '0100':
        return 'General fund'
    if a['fund'] == '2640':
        return 'Circuit breaker'
    if a['fund'] in REVOLVING:
        return 'School revolving funds'
    code = grant_code(a['fund_name'])
    if code in IDEA_CODES:
        return 'IDEA grants'
    if code in OTHER_SPED_CODES:
        return 'Other special education grants'
    raise SystemExit('journal.py: special education account %s is in fund %s %r, which no fund '
                     'group holds' % (a['account'], a['fund'], a['fund_name']))


# ---------------------------------------------------------------- 4. payees

INDIVIDUAL = 'individual (redacted)'
MASKED = object()       # a masked recipient: never a key, never a name
# Declared one at a time, each with the evidence that the two names are one payee. Empty is a
# real state: nothing beyond case, spacing and punctuation has been shown to be one payee yet.
ALIASES = {
    # The FLLAC Educational Collaborative's program is KEYSTONE, and the town’s meetings use that
    # name ("Keystone Collaborative Update", "Keystone Report"). Basis: the
    # journal's own invoice numbers on this vendor carry KEY (`23L2KEY1`, `24L2KEY4`, ...) and
    # its descriptions read `TUITION FOR KEYSTONE`; and TJ, 19 October 2026: "FLLAC is
    # Keystone." Not every FLLAC line is KEY-coded -- the contracted-services lines carry other
    # invoice numbers -- so the label names the collaborative first and the program beside it.
    'FLLAC EDUCATIONAL CO': 'FLLAC (KEYSTONE)',
}


def vendor_key(name):
    """A shown payee's name, normalised. Never called on a masked payee."""
    k = re.sub(r'\s+', ' ', name.upper()).strip().rstrip('.,;')
    return ALIASES.get(k, k)


def is_masked_payee(r):
    """A vendor line whose payee the redaction (ours or the Town's) hid."""
    return r['ref_type'] == 'VND' and r['vendor'].strip() in ('', INDIVIDUAL)


def payee(r):
    """The normalised shown payee of a line; MASKED for a hidden one; None for a line with no
    payee at all (a pay run, a journal entry, a receipt)."""
    if r['ref_type'] != 'VND':
        return None
    if is_masked_payee(r):
        return MASKED
    return vendor_key(r['vendor'])


# ---------------------------------------------------------------- 5. the surplus scope

# THE SCHOOL GENERAL FUND AS THE SURPLUS REPORTS COUNT IT: fund 0100, department 300 -- the
# scope of the period-13 `gf-school` spreadsheets, which the journal ties to the cent on every
# column in all four years. Department 301 (org 13012, curriculum adoption) is the rest of the
# district's own printed budget total and sits OUTSIDE this scope; a report on the surplus says
# so beside the figure (notes/plans/MUNIS-JOURNAL-REPORTS.md, the settled answers).
SURPLUS_DEPT = '300'
DISTRICT_DEPTS = ('300', '301')


def department(account):
    return account.split('-')[2]


def in_surplus_scope(a):
    return a['fund'] == '0100' and department(a['account']) == SURPLUS_DEPT


# What made a budget line move. A transfer (`BUA`) is one of two things, told apart by the
# description the Town gives it: the open purchase orders of the year before, re-budgeted on
# 1 July (`ENCUMBRANCE CARRY FORWARD <year>`; each equals the previous year's `YEC` close to
# the cent), or every other change -- a Town Meeting vote, a Reserve Fund transfer, a
# line-to-line move. Measured 19 October 2026 on FY2023-FY2026.
def is_carry_forward(r):
    return r['source'] == 'BUA' and r['description'].startswith('ENCUMBRANCE CARRY FORWARD')


def piece(r):
    """Which piece of a surplus bridge a line is: 'original_budget', 'carry_forward',
    'transfer', an actual's KIND_OF, or 'encumbrance'."""
    if r['posts_to'] == 'actual':
        return KIND_OF[r['source']]
    if r['posts_to'] == 'transfer':
        return 'carry_forward' if is_carry_forward(r) else 'transfer'
    return r['posts_to']


def left(rows):
    """Budget less actual less open orders: what a set of lines left unspent and uncommitted
    -- the `available_budget` the period-13 spreadsheet prints."""
    return sum((r['amt'] if r['posts_to'] in ('original_budget', 'transfer') else -r['amt']
                for r in rows), Decimal(0))


# ---------------------------------------------------------------- 6. every fund, every line

# THE FUND GROUPS of the all-funds budget (scripts/build_school_all_funds.py), read off the
# fund NUMBER the Town's chart of accounts gives each fund, never off its name. Five, because
# a chart holds five hues. Which group a fund is in is OUR grouping; the fund numbers are the
# Town's. Gift funds (1311, 1315, 15xx) and the transportation fee fund (1600) sit with the
# revolving funds, numbered beside them; 42xx and 46xx are grant funds by their names (FY26
# Title I, Title II); 30xx-31xx are capital articles, 81xx scholarships, 9002 custodian details.
FUND_GROUPS = ('General fund', 'Revolving funds and lunch', 'Circuit breaker', 'Grants',
               'Capital and other')
# Which groups carry a balance from year to year BY DESIGN, and which spend an award inside a
# period the grantor sets. A revolving fund keeps what it does not spend (M.G.L. c.44 s.53E1/2
# and the school-specific sections); a grant is drawn against an award, so an award not spent
# is money never received rather than money held.
CARRIES = {'Revolving funds and lunch': True, 'Circuit breaker': True, 'Grants': False,
           'Capital and other': True, 'General fund': False}


def fund_group(a):
    f = a['fund']
    if f == '0100':
        return 'General fund'
    if f == '2640':
        return 'Circuit breaker'
    if f[:2] in ('13', '15', '16') or f == '2200':
        return 'Revolving funds and lunch'
    if f[:2] in ('24', '25', '26', '27', '28', '29', '42', '46'):
        return 'Grants'
    if f[:2] in ('30', '31', '81', '90'):
        return 'Capital and other'
    raise SystemExit('journal.py: fund %s %r is in no fund group' % (f, a['fund_name']))


def function(account):
    """Segment 4 of the nine: the function code, the Town's version of DESE's chart."""
    return account.split('-')[3]


# WHAT A FUNCTION CODE IS, against the voted budget. Our classification, declared:
#   line      a code the general fund budget is voted on (original budget or a transfer on a
#             general fund account, in any year of the run), other than a heading
#   heading   a code ending 000 (1000, 2000, 4000), or ending 00 where the general fund budgets
#             codes beneath it but not the code itself (2300 over 2305-2357; 2400 over
#             2410-2451). It names a group of lines and no one line
#   none      0000: no function at all
#   other     a real code the voted budget has no line for (3400, food services: lunch only)
# The general fund's own few dollars on 2000 (mileage) are a heading too -- the test is the
# code, not the fund.
FUNCTION_CLASSES = ('line', 'heading', 'none', 'other')


def voted_codes():
    """The function codes the general fund budget is voted on, headings excluded."""
    if 'voted' not in _CACHE:
        A = accounts()
        codes = {function(r['account']) for r in lines()
                 if A[r['account']]['fund'] == '0100' and is_expense(A[r['account']])
                 and r['posts_to'] in ('original_budget', 'transfer') and r['amt'] != 0}
        _CACHE['voted'] = {c for c in codes if not c.endswith('000')}
    return _CACHE['voted']


def function_class(code):
    v = voted_codes()
    if code == '0000':
        return 'none'
    if code.endswith('000'):
        return 'heading'
    if code in v:
        return 'line'
    if code.endswith('00') and any(c[:2] == code[:2] and c != code for c in v):
        return 'heading'
    return 'other'


# ---------------------------------------------------------------- loading

_CACHE = {}


def accounts():
    if 'accounts' not in _CACHE:
        _CACHE['accounts'] = {a['account']: a for a in
                              csv.DictReader(open(ACCOUNTS_CSV, encoding='utf-8', newline=''))}
    return _CACHE['accounts']


def lines():
    """Every journal line, with `fy` as an int and `amt` as a Decimal. Refuses a source code
    COLUMN_OF does not hold, or a line whose posts_to disagrees with it."""
    if 'lines' not in _CACHE:
        A = accounts()
        out = []
        for r in csv.DictReader(open(JOURNAL_CSV, encoding='utf-8', newline='')):
            if COLUMN_OF.get(r['source']) != r['posts_to']:
                raise SystemExit('journal.py: %s line on page %s posts to %r; COLUMN_OF says %r'
                                 % (r['source'], r['page'], r['posts_to'],
                                    COLUMN_OF.get(r['source'])))
            if r['account'] not in A:
                raise SystemExit('journal.py: line on page %s names account %s, which the '
                                 'accounts file does not hold' % (r['page'], r['account']))
            r['fy'] = int(r['fiscal_year'])
            r['amt'] = Decimal(r['amount'])
            out.append(r)
        _CACHE['lines'] = out
    return _CACHE['lines']


def rollup(rows, *keys):
    """Sum `amt` over rows by a tuple of key functions (or field names)."""
    fs = [k if callable(k) else (lambda r, k=k: r[k]) for k in keys]
    out = defaultdict(Decimal)
    for r in rows:
        out[tuple(f(r) for f in fs)] += r['amt']
    return dict(out)


def actuals(pred=None):
    """Actual lines, optionally filtered by a predicate on (line, account)."""
    A = accounts()
    return [r for r in lines() if r['posts_to'] == 'actual'
            and (pred is None or pred(r, A[r['account']]))]


def sped_actuals(include_outside_total=False):
    """Actual lines on special education EXPENSE accounts. By default only components counted
    in the total (psychologists excluded, see COMPONENTS)."""
    def ok(r, a):
        c = component(a)
        return c is not None and (include_outside_total or c in IN_TOTAL)
    return actuals(ok)


def by_fund_object(rows):
    """THE fund-by-object rollup: (fy, fund, object) -> amount."""
    return rollup(rows, 'fy', 'fund', 'object')


def main():
    A = accounts()
    L = lines()
    print('%s lines, %s accounts' % (f'{len(L):,}', f'{len(A):,}'))
    print('classes:', dict(Counter(r['posts_to'] for r in L)))
    print('actual kinds:', dict(Counter(KIND_OF[r['source']] for r in L if r['posts_to'] == 'actual')))
    sp = [a for a in A.values() if is_sped(a)]
    print('special education list: %d accounts (%d expense, %d revenue)'
          % (len(sp), sum(is_expense(a) for a in sp), sum(is_revenue(a) for a in sp)))
    print('components:', dict(Counter(component(a) for a in sp if is_expense(a))))
    print('funds:', dict(Counter(sped_fund(a) for a in sp if is_expense(a))))
    names = defaultdict(set)
    for r in L:
        p = payee(r)
        if p is not None and p is not MASKED:
            names[p].add(r['vendor'])
    merged = {k: sorted(v) for k, v in names.items() if len(v) > 1}
    print('payees: %d shown; %d keys merge more than one printed name:' % (len(names), len(merged)))
    for k, v in sorted(merged.items()):
        print('   %s <- %s' % (k, v))


if __name__ == '__main__':
    sys.exit(main())
