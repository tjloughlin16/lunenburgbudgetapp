"""Compare the Town's function coding against the district's budget book, and report
every function code where the two do not line up.

**Both documents code the same money, and neither is treated here as correct.** The Town
Accountant's MUNIS account string carries a function code in its fourth segment
(`0100-3-300-2330-51-2-13-1-511203`); the district's budget workbook prints a function
code at the head of each group (`2330 - Paraprofessionals Special Education`). Where the
two disagree, that disagreement is the output. Which coding a given account *should*
carry is not established by anything in this repository -- DESE's chart of accounts would
settle it and we do not hold it -- so nothing here says one side is wrong.

TWO LIMITS, both of which matter for reading the output:

1.  **This compares totals, not accounts.** The budget book carries no account number, so
    a book line cannot be matched to a MUNIS account except by its amount, and 81 of its
    FY26 lines sit on an amount shared with another line. Matching on a non-key attribute
    is how this project mis-identified an account already. So the comparison stops at the
    function total, and the accounts on each side are printed for a reader to judge.

2.  **A total that ties is not evidence its components are right**, so this checks the
    components too. Inside every code whose total agrees, each ledger account is paired
    against a workbook line of the same amount, to the dollar. Two codes tie on the total
    and fail that pairing, which is exactly the case this second pass exists to catch.

    Pairing is by AMOUNT, which is not a key -- it establishes that a line of that size
    exists on both sides, and never that the two are the same line. Accounts swapped
    between two codes in opposite directions by equal amounts remain invisible. Only an
    account number on the workbook side would close that, and the workbook has none.

    python3 scripts/check_function_crosswalk.py
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
DEPT = '300'          # the school department
FY = '2026'


def money(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def pair(accounts, book_lines):
    """Pair ledger accounts to workbook lines of the same amount, within a dollar.

    The workbook states whole dollars against a ledger that states cents, so a dollar is
    the whole tolerance. Returns (accounts with no counterpart, lines with no
    counterpart). Pairing is by AMOUNT, which is not a key: it shows a line of that size
    exists on both sides, never that the two are the same line.
    """
    rest = [r for r in book_lines if abs(money(r['fy26_final'])) >= 0.5]
    loose = []
    for a in sorted((r for r in accounts if abs(money(r['original'])) >= 0.5),
                    key=lambda r: -money(r['original'])):
        j = next((i for i, b in enumerate(rest)
                  if abs(money(b['fy26_final']) - money(a['original'])) <= 1.0), None)
        if j is None:
            loose.append(a)
        else:
            rest.pop(j)
    return loose, rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='exit non-zero if any function code does not reconcile')
    args = ap.parse_args()
    ledger = [r for r in csv.DictReader(open(os.path.join(DATA, 'munis-ledger.csv')))
              if r['dept'] == DEPT and r['fy'] == FY and r['level'] == 'account'
              and r['account_type'] == 'expense']
    if not ledger:
        print('no account-grain school rows in the ledger for FY%s' % FY)
        return 1
    missing = [r for r in ledger if not r['function']]
    if missing:
        # Rule: never let a partly-populated column be summed as if it were complete.
        print('%d of %d school account rows carry no function code; the reports they '
              'came from are printed rather than exported, and the printed form does '
              'not show the account string. Not comparable.'
              % (len(missing), len(ledger)))
        for d in sorted({r['doc_id'] for r in missing}):
            print('   ', d)
        ledger = [r for r in ledger if r['function']]

    munis = collections.defaultdict(float)
    accts = collections.defaultdict(list)
    for r in ledger:
        munis[r['function']] += money(r['original'])
        accts[r['function']].append(r)

    book = collections.defaultdict(float)
    lines = collections.defaultdict(list)
    uncoded = []
    for r in csv.DictReader(open(os.path.join(DATA, 'lps-budget-lines.csv'))):
        if r['kind'] != 'line':
            continue
        m = re.match(r'\s*(\d{4})', r['function_group'] or '')
        if not m:
            # NOT skipped silently. The workbook carries at least one real budget line
            # outside every numbered group ('Salary Reserve', under a TOTAL SALARIES
            # heading). Dropping it made a MUNIS account look unmatched when the
            # workbook had it all along -- a defect in this script that read as a
            # finding about the documents.
            if abs(money(r['fy26_final'])) >= 0.5:
                uncoded.append(r)
            continue
        book[m.group(1)] += money(r['fy26_final'])
        lines[m.group(1)].append(r)

    codes = sorted(set(munis) | set(book))
    # The workbook states whole dollars, the ledger spreadsheet states cents, so a dollar
    # per account is rounding. Same tolerance as extract_munis_report.reconcile() and as
    # build_coding_questions.py, which must not report a different count from this.
    off = [c for c in codes if abs(munis[c] - book[c]) > max(1.0, float(len(accts[c])))]

    print('FY%s general fund, department %s -- function coding, two documents\n' % (FY, DEPT))
    print('  %-6s %6s %14s %16s %13s' % ('func', 'accts', 'MUNIS approp',
                                         'book fy26_final', 'difference'))
    for c in codes:
        d = munis[c] - book[c]
        print('  %-6s %6d %14s %16s %13s%s'
              % (c, len(accts[c]), f'{munis[c]:,.0f}', f'{book[c]:,.0f}',
                 f'{d:,.0f}', '   <-- differs' if c in off else ''))
    print('\n  %d of %d function codes carry the same total in both documents '
          '(a dollar per account is rounding, not a difference).'
          % (len(codes) - len(off), len(codes)))
    print('  MUNIS total %s   book total %s   difference %s'
          % (f'{sum(munis.values()):,.0f}', f'{sum(book.values()):,.0f}',
             f'{sum(munis.values()) - sum(book.values()):,.0f}'))

    print('\n\nWhere they differ, what each document has under that code')
    print('(the two sides are NOT matched account to account -- see the limits above)')
    for c in off:
        print('\n--- function %s   MUNIS %s   book %s   difference %s'
              % (c, f'{munis[c]:,.0f}', f'{book[c]:,.0f}',
                 f'{munis[c] - book[c]:,.0f}'))
        print('    MUNIS accounts:' if accts[c] else '    MUNIS accounts: none')
        for r in sorted(accts[c], key=lambda r: -money(r['original'])):
            print('      %-34s %-11s %12s' % (r['account'], r['name'],
                                              f"{money(r['original']):,.0f}"))
        print('    budget book lines:' if lines[c] else '    budget book lines: none')
        for r in sorted(lines[c], key=lambda r: -money(r['fy26_final'])):
            print('      %-46s %12s' % (r['line_item'][:46],
                                        f"{money(r['fy26_final']):,.0f}"))

    # A mismatch is not smoothed over, averaged away, or explained by this script. Two
    # documents state different amounts for the same code in the same year, and one of
    # them is wrong. Until the coding is corrected at source, this fails.
    # Second pass: inside the codes whose totals agree, does every account have a
    # counterpart of the same size?
    split = [(c,) + pair(accts[c], lines[c]) for c in codes if c not in off]
    split = [t for t in split if t[1] or t[2]]
    if uncoded:
        print('\n\nBudget-book lines carrying NO function code')
        print('  (the workbook heads these with a section title rather than a code, so '
              'they are in no column above)')
        for r in sorted(uncoded, key=lambda r: -money(r['fy26_final'])):
            print('      row %-5s %-46s %12s   [%s]'
                  % (r['row'], r['line_item'].strip()[:46],
                     f"{money(r['fy26_final']):,.0f}", (r['function_group'] or '')[:22]))

    # The department control total, which is what would have caught the above. Every
    # budget-book line, coded or not, against every ledger account.
    led_tot = sum(money(r['original']) for r in ledger)
    bk_tot = sum(book.values()) + sum(money(r['fy26_final']) for r in uncoded)
    print('\n\nDepartment control total, every line on both sides')
    print('      MUNIS ledger, %d accounts        %14s' % (len(ledger), f'{led_tot:,.2f}'))
    print('      budget book, coded + uncoded     %14s' % f'{bk_tot:,.2f}')
    print('      difference                       %14s' % f'{led_tot - bk_tot:,.2f}')

    print('\n\nCodes whose TOTAL agrees but whose lines do not pair')
    if not split:
        print('  none -- inside every tying code, each account has a workbook line of '
              'the same amount.')
    for c, la, lb in split:
        print('\n--- function %s   total %s on both sides'
              % (c, f'{munis[c]:,.0f}'))
        for a in la:
            print('      ledger account with no workbook line of that amount   '
                  '%-34s %-11s %10s'
                  % (a['account'], a['name'].strip(), f"{money(a['original']):,.0f}"))
        for b in lb:
            print('      workbook line with no ledger account of that amount   %-46s %10s'
                  % (b['line_item'].strip()[:46], f"{money(b['fy26_final']):,.0f}"))
    print('\n  %d of %d tying codes pair line for line.'
          % (len(codes) - len(off) - len(split), len(codes) - len(off)))

    print('\n%d function code(s) do not reconcile. %s is stated under a code in one '
          'document and not the other.'
          % (len(off), f'${sum(abs(munis[c] - book[c]) for c in off):,.0f}'))
    print('Nothing here establishes which document is correct. It establishes that they '
          'cannot both be.')
    if split:
        print('%d further code(s) agree on the total and not on the lines inside.'
              % len(split))
    if (off or split) and args.check:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
