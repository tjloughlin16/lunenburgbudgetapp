#!/usr/bin/env python3
"""ONE PAGE PER FUNCTION CODE: /school-functions/<code>.

    python3 scripts/build_function_pages.py
    python3 scripts/build_function_pages.py --check

TJ, 2 November 2026, on the ranking of grant salaries by budget line: *"i need to be able to click
on things like '2000 Instruction (heading only)' and it brings up the fund page. for any of these
(liek 3510 athletics, etc). i have no idea what these are, but i want to see everything associated
to them. if they are expensed, type of accounts, just memos, etc"*

WHAT A FUNCTION CODE IS. The fourth of the nine segments of every school account number
(`0100-3-300-`**`3510`**`-...`): the Town's version of DESE's chart of accounts, saying what the
money is FOR -- 3510 athletics, 2000 instruction. Every account in every fund carries one, so one
code collects general fund lines, grants, revolving funds and lunch together. Whether a code is a
line the budget votes, a heading over several lines, or no function at all is OUR classification,
declared in journal.py (FUNCTION_CLASSES), and the page says so.

WHAT IS ON A PAGE, all of it read off the school journal (munis-school-journal.csv, our redacted
reading of the Town's Report 1), FY2023 onward:

  totals     per year: budget (original plus transfers), spent (payments plus what is still
             owed: journal.SPENT, the site's definition), split by kind of entry -- payroll,
             invoices, journal entries, receipts credited back, purchase orders still open
  by group   spent per year by fund group (general fund, grants, revolving funds and lunch...)
  accounts   every EXPENSE account carrying the code, with its fund, programme, and a link to its
             school line page or fund page where one exists (scripts/fy_items.py index)
  payees     who was paid, from invoices; a masked recipient is counted, never named
  memos      every journal entry (GEN/GRV): the date, the account and the memo as printed

Revenue accounts are not on these pages: 345 of the journal's 347 carry code 0000, because a
receipt has no purpose, so they would make "no function code" read as a spending total.

ASSERTED, or nothing is written (line accounting -- there is no printed total per code):
  * every expense journal line lands on exactly one code, and the codes sum to the journal
  * on each page, per year, accounts, fund groups and kinds of entry each sum to the same spent
  * every name in the index has a page and every page is in the index

    /data/fy-breakdown/functions.json           every code: code, name, class, years, totals
    /data/fy-breakdown/function/<code>.json     one code, all years
"""
import argparse
import string
import json
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402
from build_school_all_funds import code_names  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown')
INDEX = os.path.join(OUT_DIR, 'functions.json')
ITEMS = os.path.join(OUT_DIR, 'index.json')
BOOK = os.path.join(ROOT, 'sources', 'data', 'lps-budget-lines.csv')
D0 = Decimal(0)
CENT = Decimal('0.01')

# What each class means, in a sentence a reader can use. Ours (journal.py FUNCTION_CLASSES).
CLASS_TEXT = {
    'line': 'A line the school budget votes on. Town Meeting sees this code as a budget line.',
    'heading': 'A heading, not a line: it names a group of lines (2000 is all of instruction), '
               'so money booked here is on no single voted line.',
    'none': 'No function at all. The account does not say what the money was for.',
    'other': 'A real code the voted school budget has no line for (food services is paid from '
             'lunch money, not the budget).',
}
CLASS_SHORT = {'line': 'Voted budget line', 'heading': 'Heading only', 'none': 'No function code',
               'other': 'Not in the voted budget'}
# The kinds of entry, in the order a reader meets them. `owed` is every encumbrance source.
KINDS = [('payroll', 'Payroll'), ('invoice', 'Invoices'), ('journal entry', 'Journal entries'),
         ('receipt', 'Receipts credited back'), ('owed', 'Purchase orders still owed')]


def fail(msg):
    raise SystemExit('build_function_pages.py: ' + msg)


def money(v):
    return ('-$%s' if v < 0 else '$%s') % format(abs(v).quantize(CENT), ',.2f')


def kind_of(r):
    return 'owed' if r['posts_to'] == 'encumbrance' else J.KIND_OF[r['source']]


def book_names():
    """The district budget book's own name for each code, `2357 - Professional Dev`, as printed.
    Used only where DESE's EOYR rows give the code no name (code_names), and labelled as the book's."""
    import csv
    import re
    out = {}
    for r in csv.DictReader(open(BOOK, encoding='utf-8')):
        m = re.match(r'(\d{4}) - (.+)', r['function_group'] or '')
        if m:
            out.setdefault(m.group(1), m.group(2).strip())
    return out


def links():
    """Where an account's own page is: a school line by account number, a fund by programme name."""
    ix = json.load(open(ITEMS, encoding='utf-8'))
    line_by_acct = {}
    for ln in ix['lines']:
        line_by_acct[ln['account']] = '/school-lines/' + ln['slug']
    fund_by_name = {f['name']: '/school-funds/' + f['slug'] for f in ix['funds']}
    return line_by_acct, fund_by_name


def build():
    A, L = J.accounts(), J.lines()
    names, name_by = code_names(), {}
    for c, n in book_names().items():
        if c not in names:
            names[c] = n
            name_by[c] = 'the district budget book'
    years = sorted({r['fy'] for r in L})
    line_by_acct, fund_by_name = links()

    exp = [r for r in L if J.is_expense(A[r['account']])]
    by_code = defaultdict(list)
    for r in exp:
        by_code[J.function(r['account'])].append(r)
    if sum(len(v) for v in by_code.values()) != len(exp):
        fail('expense lines do not land on exactly one code each')
    missing = sorted(c for c in by_code if c not in names)
    if missing:
        fail('function code(s) with no name: %s (neither the DESE EOYR nor the district budget book names it)'
             % ', '.join(missing))

    outs, index = {}, []
    grand = D0
    for c in sorted(by_code):
        rows = by_code[c]
        spent = defaultdict(lambda: D0)
        budget = defaultdict(lambda: D0)
        kinds = defaultdict(lambda: D0)          # (fy, kind)
        counts = Counter()                       # (fy, kind) -> lines
        groups = defaultdict(lambda: D0)         # (fy, group)
        acct_s = defaultdict(lambda: D0)         # (account, fy)
        acct_b = defaultdict(lambda: D0)
        acct_n = Counter()
        pay = defaultdict(lambda: D0)            # (payee, fy)
        pay_n = Counter()
        memos = []
        for r in rows:
            a, y = A[r['account']], r['fy']
            if r['posts_to'] in ('original_budget', 'transfer'):
                budget[y] += r['amt']
                acct_b[(r['account'], y)] += r['amt']
                continue
            if not J.is_spent(r):
                fail('line on page %s is neither budget nor spent' % r['page'])
            k = kind_of(r)
            spent[y] += r['amt']
            kinds[(y, k)] += r['amt']
            counts[(y, k)] += 1
            groups[(y, J.fund_group(a))] += r['amt']
            acct_s[(r['account'], y)] += r['amt']
            acct_n[r['account']] += 1
            if r['source'] in ('API', 'APM'):
                p = J.payee(r)
                key = J.INDIVIDUAL if p is J.MASKED else (p or '(no payee printed)')
                pay[(key, y)] += r['amt']
                pay_n[key] += 1
            if r['source'] in ('GEN', 'GRV'):
                memos.append(dict(fy='FY%d' % y, date=r['effective_date'], account=r['account'],
                                  desc=string.capwords(a['account_description']), memo=r['description'].strip(),
                                  amount=money(r['amt']), journal=r['journal'],
                                  v=float(r['amt'])))
        grand += sum(spent.values())

        # line accounting, per year: three breakdowns, one total
        for y in years:
            for what, part in (('kinds', sum(v for (yy, _), v in kinds.items() if yy == y)),
                               ('fund groups', sum(v for (yy, _), v in groups.items() if yy == y)),
                               ('accounts', sum(v for (_, yy), v in acct_s.items() if yy == y))):
                if part != spent[y]:
                    fail('%s FY%d: %s sum to %s, spent is %s' % (c, y, what, part, spent[y]))

        accts = sorted({k for k, _ in acct_s} | {k for k, _ in acct_b},
                       key=lambda k: (-sum(acct_s[(k, y)] for y in years), k))
        acct_rows = []
        for k in accts:
            a = A[k]
            prog = J.grant_program(a)
            href = line_by_acct.get(k) or (fund_by_name.get(prog) if prog != 'General fund' else None)
            acct_rows.append(dict(
                account=k, desc=string.capwords(a['account_description']), group=J.fund_group(a),
                program=prog, href=href, lines=acct_n[k],
                spent=[money(acct_s[(k, y)]) if acct_s[(k, y)] else None for y in years],
                budget=[money(acct_b[(k, y)]) if acct_b[(k, y)] else None for y in years],
                total=money(sum(acct_s[(k, y)] for y in years))))
        payees = sorted({p for p, _ in pay}, key=lambda p: (-sum(pay[(p, y)] for y in years), p))
        pay_rows = [dict(name=p, lines=pay_n[p], href=None,
                         spent=[money(pay[(p, y)]) if pay[(p, y)] else None for y in years],
                         total=money(sum(pay[(p, y)] for y in years))) for p in payees]
        memos.sort(key=lambda m: (m['date'], m['journal'], m['account'], m['v']))
        for m in memos:
            del m['v']
        gnames = [g for g in J.FUND_GROUPS if any(groups[(y, g)] for y in years)]
        cls = J.function_class(c)
        page = dict(
            code=c, name=names[c], name_by=name_by.get(c, 'DESE'), cls=cls, cls_short=CLASS_SHORT[cls], cls_text=CLASS_TEXT[cls],
            years=['FY%d' % y for y in years],
            totals=[dict(fy='FY%d' % y, spent=money(spent[y]), budget=money(budget[y]) if budget[y] else None,
                         kinds={k: money(kinds[(y, k)]) for k, _ in KINDS if kinds[(y, k)]},
                         counts={k: counts[(y, k)] for k, _ in KINDS if counts[(y, k)]})
                    for y in years],
            kinds=[dict(id=k, label=l) for k, l in KINDS],
            groups=[dict(name=g, spent=[money(groups[(y, g)]) if groups[(y, g)] else None for y in years],
                         v=[float(groups[(y, g)]) for y in years]) for g in gnames],
            accounts=acct_rows, payees=pay_rows, memos=memos,
            four_years=money(sum(spent.values())),
            sources=[dict(href=J.PUBLIC['journal'],
                          label='munis-school-journal.csv -- every school journal line, every fund, '
                                'our redacted reading of the Town’s Report 1'),
                     dict(href=J.PUBLIC['accounts'], label='munis-school-journal-accounts.csv')])
        outs[os.path.join(OUT_DIR, 'function', c + '.json')] = dump(page)
        index.append(dict(code=c, name=names[c], cls=cls, cls_short=CLASS_SHORT[cls],
                          four_years=page['four_years'], accounts=len(acct_rows)))

    total = sum(r['amt'] for r in exp if J.is_spent(r))
    if grand != total:
        fail('the codes sum to %s, the journal to %s' % (grand, total))
    outs[INDEX] = dump(dict(years=['FY%d' % y for y in years], functions=index))
    return outs


def dump(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = build()
    d = os.path.join(OUT_DIR, 'function')
    gone = sorted(os.path.join(d, f) for f in (os.listdir(d) if os.path.isdir(d) else [])
                  if f.endswith('.json') and os.path.join(d, f) not in outs)
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        stale += ['%s (no longer written)' % os.path.relpath(p, ROOT) for p in gone]
        if stale:
            print('STALE %s' % ', '.join(stale[:5]), file=sys.stderr)
            return 1
        print('function pages: current (%d codes)' % (len(outs) - 1))
        return 0
    for p in gone:
        os.remove(p)
    for p, t in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
        os.replace(p + '.tmp', p)
    print('wrote %d function pages and %s' % (len(outs) - 1, os.path.relpath(INDEX, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
