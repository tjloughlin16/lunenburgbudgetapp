#!/usr/bin/env python3
"""Check the PEG Access / Public Access Cable statements we READ against what they PRINT.

    python3 scripts/verify_peg_access.py

WHAT THIS MONEY IS -- AND WHAT IT IS NOT

PEG Access money is the franchise fee Comcast pays the Town under its cable licence, plus
the interest that money earns. **It is paid by cable subscribers, not by taxpayers, and it
is not available to the town's general operations.** Rule 11 in its plainest form: a
sentence putting a PEG balance next to a school budget gap compares two things that cannot
be spent on each other. From FY2020 it sits in a statutory enterprise fund and is
appropriated by its own Town Meeting article, separately from the omnibus budget.

THE FUND CHANGED ITS LEGAL FORM MID-SERIES, AND THE HEADING DID NOT SAY SO

FY2015-FY2020 the reports head this `Public Access Cable`; FY2021-FY2022 `PEG Access
Enterprise Fund`; FY2023 `PEG access (Public Access Cable)`; FY2025 `Public Access Cable`
again. The renaming is NOT what happened. What happened is on page 8591 of the FY2019
annual report, in the Annual Town Meeting warrant:

    ARTICLE 16. To see if the Town will vote to establish, under Chapter 44, S53F 1/2, a
    Public Educational Government (PEG) Access Enterprise Fund, and transfer in to such
    fund all funds remaining in the Public Educational Government (PEG) Access and Cable
    Related Receipts Reserved For Appropriation Fund and the Comcast Tech Capital Grant
    Fund as of June 30, 2019 ... VOTED UNANIMOUSLY

So through FY2019 this was a receipts-reserved-for-appropriation fund plus a separate
Comcast Tech Capital Grant Fund; from FY2020 it is one enterprise fund. The money is
continuous. The FUND is not, the STATEMENT is not, and the headings track neither.

WHY THE BALANCE SERIES IS NOT A SERIES

`Starting Balance` does not mean the same thing in every edition, and nothing on the page
says which meaning is in force:

  FY2015-FY2019  it is the prior edition's own Ending Balance, and it matches it exactly.
  FY2021         it is 272,000.00 -- the BUDGET, as the same page's prose states outright:
                 "The budget starting balance was set at $272,000 for FY21 projected
                 expenses and capital costs."  Rule 1: that is an appropriation, not a
                 balance carried forward.
  FY2022         there is no starting balance row at all, so `TOTAL` is the year's
                 revenue less the year's expenses and not a fund balance.
  FY2025         `Beginning Balance` is again the budget (208,772), and `Ending Balance`
                 is that budget less expenses.

This verifier therefore REPORTS year-to-year continuity and does not fail on it. What it
fails on is arithmetic each page states about itself.

THE CHECKS

  1. LINE-ITEM FOOTING. The expense lines must sum to the TOTAL the report prints for
     them, to the cent. Independent of us: the town printed the total.

  2. PERCENT FOOTING. Where the table prints a `% of Expense` column it also prints
     100.00%, and the column must add to it.

  3. EVERY PRINTED PERCENT, RECOMPUTED from its own amount over the printed total.

  4. THE IDENTITIES THE STATEMENT STATES ABOUT ITSELF, read off the page and recorded in
     `peg-access-identities.csv` over the printed row ORDINALS -- because the arithmetic
     differs every few years and two rows in FY2019 carry the identical label `Subtotal`.

  5. EVERY PRINTED ROW TAKES PART IN AN IDENTITY. A row that no identity reaches is a row
     the page prints and does not use, which is a finding; FY2020's second `Subtotal` is
     one, and it is pinned below.

  6. THE TWO PAGES OF THE SAME REPORT AGREE ON TOTAL EXPENSES. The line-item table's
     TOTAL and the statement's `Expenses` row are printed on different pages from the same
     workbook, so they are an independent cross-check on each other.

  7. WHAT THE PROSE SAYS THE FIGURE IS. Four editions restate the previous year's Comcast
     revenue in a sentence; it must equal what that edition printed in its own table.
     FY2017's prose restates its OWN year and disagrees with its own table by $40.00.

A YEAR THAT DOES NOT TIE IS NOT WRITTEN DOWN HERE. `append_peg_access_year.py` refuses it.

SIGN CONVENTION. Nothing in any of these eleven statements is printed in parentheses or
with a minus sign; every figure is positive, including FY2022's `TOTAL`, which is a
surplus. Check 8 asserts that the parenthesisation of each raw `quote` matches the sign of
the amount stored beside it, in both directions, so the first negative to appear cannot be
stored positive -- a missed parenthesis has already cost this repository $315,772.
"""

import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, 'sources', 'data', 'peg-access.csv')
TOTALS = os.path.join(ROOT, 'sources', 'data', 'peg-access-printed-totals.csv')
IDENTITIES = os.path.join(ROOT, 'sources', 'data', 'peg-access-identities.csv')

CENT = 0.005
DOLLAR = 1.00        # a statement printed in whole dollars, against a total in cents
PCT_LINE = 0.011     # one printed percent against its own recomputation
PCT_FOOT = 0.05      # a column of rounded percents against the printed 100.00%

# PRINTED STATEMENTS THAT DO NOT AGREE WITH THEMSELVES.
#
# Where the town's own pages disagree that is a fact about the REPORT, not an error in this
# reading, and it is recorded with the amount pinned EXACTLY. If a discrepancy changes by a
# penny the check fails again, because a new error hiding inside an old allowance is what an
# exception list exists to prevent. Nothing here is adjusted to make it tie.
#
# Keyed (edition, check, key).
PRINTED_DEFECTS = {
    ('FY2017', 'line_item_footing', 'TOTAL'): (
        450.01,
        'The ten printed expense lines add to 74,665.74. The printed TOTAL is 74,215.73 -- '
        '450.01 lower. 450.00 of that is `Vendor Expenses $450.00`, the last line above '
        'the total: the pie on printed page 69 gives a percentage for the other NINE lines '
        'and none for Vendor Expenses, and those nine percentages add to exactly 100.00, so '
        'the total and the chart both exclude the same line. The remaining 0.01 is not '
        'explained by that: the nine included lines add to 74,215.74 and the page prints '
        '74,215.73. WHAT IS NOT ESTABLISHED: whether Vendor Expenses was paid and left out '
        'of the total, or was never paid and left in the table, and where the cent went. '
        'Both the statement on page 69 and the FY2018 report use 74,215.73, so the printed '
        'total is what the rest of the record is built on. The document that would settle '
        'it is the Town Accountant\'s FY2017 year-end detail for the PEG Access and Cable '
        'Related Receipts Reserved for Appropriation Fund, which the annual report does '
        'not contain.'),
    ('FY2017', 'prose_same_year', 'REVENUE STATED IN PROSE'): (
        40.00,
        'Printed page 68 says "The overall payments received for FY17 were $107,849.80." '
        'Printed page 69 says "$107,889.80" and the FY17 REVENUE vs EXPENSES table prints '
        '107,889.80 in its Revenue row. The two pages of the same report differ by $40.00 '
        'on the same quantity. The table\'s figure is the one the rest of the statement '
        'foots to (270,235.70 + 107,889.80 = 378,125.50, as printed), so the prose is the '
        'odd one out -- but nothing on either page says so.'),
    ('FY2020', 'cross_page_expenses', 'Expenses'): (
        0.32,
        'Both tables are on printed page 75. `FY20 Line Item Expenses by Percentage` foots '
        'to Total $116,933.22 and `FY20 REVENUE vs EXPENSES` prints Expenses $116,933.54 -- '
        '32 cents apart, on one page, for the same year. The line-item table foots to its '
        'own printed total exactly, and the statement foots to its own printed Total '
        'exactly (699,875.47 - 116,933.54 = 582,941.93), so each table is internally right '
        'and they disagree with each other. WHAT IS NOT ESTABLISHED: which figure is the '
        'year\'s expenses.'),
    ('FY2020', 'orphan_row', '5'): (
        449041.36,
        'The statement prints a row labelled `Subtotal` at 449,041.36 between Expenses and '
        'Total, and no arithmetic on the page reaches it: 699,875.47 - 116,933.54 = '
        '582,941.93, which is the Total printed below it. 449,041.36 is the figure FY2019\'s '
        'statement prints in the same position, one edition earlier. WHAT IS NOT '
        'ESTABLISHED: whether the row was left in from the prior year\'s workbook or means '
        'something the page does not say. It is recorded and not removed.'),
    ('FY2024', 'cross_page_expenses', 'Expenses'): (
        1.16,
        'The statement on printed page 63 prints Expenses $174,150; the line-item table on '
        'printed page 64 foots to Total $174,151.16. The statement is printed in whole '
        'dollars throughout, and rounding or truncating 174,151.16 gives 174,151, not '
        '174,150 -- so this is $1.16 apart rather than a display rounding. FY2025, printed '
        'the same way, is 97 cents apart and consistent with truncation. WHAT IS NOT '
        'ESTABLISHED: which figure the fund actually spent.'),
}


def num(v):
    v = (v or '').strip()
    return float(v) if v else 0.0


def load():
    for p in (READ, TOTALS, IDENTITIES):
        if not os.path.exists(p):
            sys.exit(f'{os.path.relpath(p, ROOT)} is missing')
    rows = list(csv.DictReader(open(READ, newline='', encoding='utf-8')))
    printed = list(csv.DictReader(open(TOTALS, newline='', encoding='utf-8')))
    idents = list(csv.DictReader(open(IDENTITIES, newline='', encoding='utf-8')))
    return rows, printed, idents


def defect(ed, check, key, delta):
    """Return the recorded defect if `delta` matches it exactly, else None."""
    known = PRINTED_DEFECTS.get((ed, check, key))
    if known and abs(abs(delta) - known[0]) <= CENT:
        return known
    return None


def parse_identity(expr):
    """'1 + 2 = 3' -> ([(+1,'1'),(+1,'2')], '3').  Ordinals as strings, signs as ints."""
    lhs, rhs = [s.strip() for s in expr.split('=')]
    terms, sign = [], 1
    for tok in re.split(r'\s*([+-])\s*', lhs):
        tok = tok.strip()
        if tok == '+':
            sign = 1
        elif tok == '-':
            sign = -1
        elif tok:
            terms.append((sign, tok))
            sign = 1
    return terms, rhs


def check_edition(ed, rows, printed, idents, out):
    fails = 0
    mine = [r for r in rows if r['edition'] == ed]
    tot = [p for p in printed if p['edition'] == ed]
    li_total = [p for p in tot if p['statement'] == 'line_item_expenses']
    stmt = sorted((p for p in tot if p['statement'] == 'revenue_vs_expenses'),
                  key=lambda p: int(p['ordinal']))
    prose = [p for p in tot if p['statement'] == 'prose']

    pages = ', '.join(sorted({f"{p['page_printed']} (pdf {p['page_pdf']})" for p in tot},
                             key=lambda s: int(s.split()[0])))
    out(f'\n{ed} — {len(mine)} expense lines, {len(stmt)} statement rows, '
        f'printed page(s) {pages}')

    # 1. THE EXPENSE LINES FOOT TO THE TOTAL THE REPORT PRINTS FOR THEM.
    if len(li_total) != 1:
        out(f'  FAIL  the report prints {len(li_total)} line-item totals; expected 1')
        return fails + 1
    lt = li_total[0]
    got = sum(num(r['amount']) for r in mine)
    want = num(lt['amount'])
    d = got - want
    known = defect(ed, 'line_item_footing', lt['total_row'], d)
    if abs(d) <= CENT:
        out(f'  ok    line items foot   {got:>14,.2f}  printed {want:>14,.2f}  {d:+,.2f}')
    elif known:
        out(f'  note  line items foot   {got:>14,.2f}  printed {want:>14,.2f}  {d:+,.2f}')
        out(f'        EXAMINED — {known[1]}')
    else:
        fails += 1
        out(f'  FAIL  line items foot   {got:>14,.2f}  printed {want:>14,.2f}  {d:+,.2f}')

    # 2 and 3. THE PERCENT COLUMN, WHERE THE TABLE PRINTS ONE.
    pcts = [r for r in mine if r['pct'] != '']
    if pcts:
        if lt['pct'] == '':
            fails += 1
            out('  FAIL  percents are recorded on the lines but the table prints no total '
                'percent')
        else:
            s = sum(num(r['pct']) for r in pcts)
            d = s - num(lt['pct'])
            ok = abs(d) <= PCT_FOOT
            fails += 0 if ok else 1
            out(f'  {"ok  " if ok else "FAIL"}  percents foot     {s:>14,.2f}%  '
                f'printed {num(lt["pct"]):>13,.2f}%  {d:+,.2f}')
        bad = 0
        for r in pcts:
            exp = num(r['amount']) / want * 100.0 if want else 0.0
            if abs(exp - num(r['pct'])) > PCT_LINE:
                bad += 1
                fails += 1
                out(f'  FAIL  {r["line"]}: printed {num(r["pct"]):.2f}%, '
                    f'{num(r["amount"]):,.2f} of {want:,.2f} is {exp:.4f}%')
        if not bad:
            out(f'  ok    every one of {len(pcts)} printed percents recomputes from its '
                f'own amount over the printed total')

    # 4. THE IDENTITIES THE STATEMENT STATES ABOUT ITSELF.
    by_ord = {p['ordinal']: p for p in stmt}
    mine_id = [i for i in idents if i['edition'] == ed]
    if not mine_id:
        fails += 1
        out('  FAIL  no identity is recorded for this statement; a statement nothing '
            'reconciles is not checked')
    used = set()
    for i in mine_id:
        terms, rhs = parse_identity(i['identity'])
        missing = [o for _, o in terms] + [rhs]
        missing = [o for o in missing if o not in by_ord]
        if missing:
            fails += 1
            out(f'  FAIL  identity {i["identity"]}: no printed row at ordinal '
                f'{", ".join(missing)}')
            continue
        used.update(o for _, o in terms)
        used.add(rhs)
        lhs = sum(sign * num(by_ord[o]['amount']) for sign, o in terms)
        d = lhs - num(by_ord[rhs]['amount'])
        ok = abs(d) <= CENT
        fails += 0 if ok else 1
        names = ' '.join(('+' if s > 0 else '-') + ' ' + by_ord[o]['total_row']
                         for s, o in terms).lstrip('+ ')
        out(f'  {"ok  " if ok else "FAIL"}  {i["identity"]:16} {lhs:>14,.2f}  '
            f'printed {num(by_ord[rhs]["amount"]):>14,.2f}  {d:+,.2f}   '
            f'{names} = {by_ord[rhs]["total_row"]}')

    # 5. EVERY PRINTED ROW IS REACHED BY SOME IDENTITY.
    for p in stmt:
        if p['ordinal'] in used:
            continue
        known = defect(ed, 'orphan_row', p['ordinal'], num(p['amount']))
        if known:
            out(f'  note  row {p["ordinal"]} `{p["total_row"]}` {num(p["amount"]):,.2f} '
                f'takes part in no identity on the page')
            out(f'        EXAMINED — {known[1]}')
            continue
        fails += 1
        out(f'  FAIL  row {p["ordinal"]} `{p["total_row"]}` {num(p["amount"]):,.2f} takes '
            f'part in no arithmetic the page states')

    # 6. THE TWO PAGES OF THE SAME REPORT ON TOTAL EXPENSES.
    exp_rows = [p for p in stmt if p['total_row'] == 'Expenses']
    if len(exp_rows) != 1:
        fails += 1
        out(f'  FAIL  the statement prints {len(exp_rows)} rows labelled Expenses; '
            f'expected 1')
    else:
        e = exp_rows[0]
        tol = CENT if e['precision'] == 'cents' else DOLLAR
        d = want - num(e['amount'])
        known = defect(ed, 'cross_page_expenses', 'Expenses', d)
        same = e['page_printed'] == lt['page_printed']
        where = ('both on printed page %s' % lt['page_printed'] if same
                 else 'printed pages %s and %s' % (lt['page_printed'], e['page_printed']))
        if abs(d) <= tol:
            out(f'  ok    expenses agree   {want:>14,.2f}  statement '
                f'{num(e["amount"]):>12,.2f}  {d:+,.2f}   ({where})')
        elif known:
            out(f'  note  expenses differ  {want:>14,.2f}  statement '
                f'{num(e["amount"]):>12,.2f}  {d:+,.2f}   ({where})')
            out(f'        EXAMINED — {known[1]}')
        else:
            fails += 1
            out(f'  FAIL  expenses differ  {want:>14,.2f}  statement '
                f'{num(e["amount"]):>12,.2f}  {d:+,.2f}   ({where})')

    # 7. WHAT THE PROSE SAYS, AGAINST WHAT THE TABLE PRINTS.
    for p in prose:
        if p['total_row'] == 'REVENUE STATED IN PROSE':
            rev = [s for s in stmt if s['total_row'].startswith('Revenue')
                   and s['total_row'] != 'Revenue Total']
            if len(rev) != 1:
                fails += 1
                out('  FAIL  prose restates this year\'s revenue but the table prints '
                    f'{len(rev)} revenue rows')
                continue
            d = num(p['amount']) - num(rev[0]['amount'])
            known = defect(ed, 'prose_same_year', p['total_row'], d)
            if abs(d) <= CENT:
                out(f'  ok    prose agrees with the table on this year\'s revenue '
                    f'{num(p["amount"]):,.2f}')
            elif known:
                out(f'  note  prose says {num(p["amount"]):,.2f}, the table prints '
                    f'{num(rev[0]["amount"]):,.2f}  ({d:+,.2f})')
                out(f'        EXAMINED — {known[1]}')
            else:
                fails += 1
                out(f'  FAIL  prose says {num(p["amount"]):,.2f}, the table prints '
                    f'{num(rev[0]["amount"]):,.2f}  ({d:+,.2f})')

    # 8. THE SIGN CONVENTION, BOTH WAYS. Cells only: a `prose` row's quote is a SENTENCE,
    # and sentences here contain parentheses that are not accounting negatives -- FY2023's
    # is "...the previous year's $199,956.37 (2 % over FY22)".
    for r in mine + [p for p in tot if p['statement'] != 'prose']:
        q, a = r.get('quote', ''), num(r['amount'])
        if ('(' in q) != (a < 0):
            fails += 1
            out(f'  FAIL  sign: quote {q!r} and amount {a:,.2f} disagree about the sign')
    return fails


def check_prior_year(rows, printed, out):
    """Each edition that restates LAST year's Comcast revenue, against what that edition
    printed. Four of them do, and it is the only cross-edition check the reports make."""
    fails = 0
    out('\n--    what each report says the PREVIOUS year\'s Comcast revenue was, against '
        'what that year printed')
    said = [p for p in printed if p['total_row'] == 'PRIOR YEAR REVENUE STATED']
    if not said:
        out('  FAIL  no edition restates a prior year; the cross-edition check has nothing '
            'to do')
        return 1
    for p in sorted(said, key=lambda p: int(p['fy'])):
        prev = 'FY%d' % (int(p['fy']) - 1)
        rev = [s for s in printed if s['edition'] == prev
               and s['statement'] == 'revenue_vs_expenses'
               and s['total_row'].startswith('Revenue')
               and s['total_row'] != 'Revenue Total']
        if len(rev) != 1:
            fails += 1
            out(f'  FAIL  {p["edition"]} restates {prev} but {prev} prints {len(rev)} '
                f'revenue rows')
            continue
        d = num(p['amount']) - num(rev[0]['amount'])
        ok = abs(d) <= CENT
        fails += 0 if ok else 1
        out(f'  {"ok  " if ok else "FAIL"}  {p["edition"]} says {prev} was '
            f'{num(p["amount"]):>12,.2f}; {prev} printed {num(rev[0]["amount"]):>12,.2f}  '
            f'{d:+,.2f}')
    return fails


def report_continuity(printed, out):
    """REPORTED, NOT CHECKED. See the module docstring: `Starting Balance` means the prior
    year's ending balance in some editions and the year's BUDGET in others, so a failure
    here would be a failure to read the page rather than a failure of the page."""
    out('\n--    year to year: what each statement carried in, against what the one before '
        'it carried out')
    out('      (REPORTED, not a pass/fail check -- the fund changed form in FY2020 and '
        '`Starting Balance` changes meaning with it)')
    eds = sorted({int(p['fy']) for p in printed})
    for fy in eds:
        prev = [p for p in printed if int(p['fy']) == fy - 1
                and p['statement'] == 'revenue_vs_expenses'
                and p['total_row'] in ('Ending Balance', 'Total', 'TOTAL', 'Balance')]
        cur = [p for p in printed if int(p['fy']) == fy
               and p['statement'] == 'revenue_vs_expenses'
               and p['total_row'] in ('Starting Balance', 'Beginning Balance')]
        if not prev or not cur:
            continue
        a, b = num(prev[-1]['amount']), num(cur[0]['amount'])
        mark = 'carries' if abs(a - b) <= CENT else 'BREAKS '
        out(f'  {mark}  FY{fy - 1} {prev[-1]["total_row"]:<12} {a:>14,.2f}  ->  '
            f'FY{fy} {cur[0]["total_row"]:<17} {b:>14,.2f}  {b - a:+,.2f}')


def main():
    rows, printed, idents = load()
    editions = sorted({r['edition'] for r in rows}, key=lambda e: int(e[2:]))
    if not editions:
        sys.exit('peg-access.csv holds no rows')
    fails = sum(check_edition(ed, rows, printed, idents, print) for ed in editions)
    fails += check_prior_year(rows, printed, print)
    report_continuity(printed, print)

    print(f'\n{len(editions)} edition(s) checked, {fails} failure(s)')
    if fails:
        sys.exit(1)
    n = sum(1 for k in PRINTED_DEFECTS if k[0] in editions)
    print("Every expense table foots to the total its own report prints, every printed")
    print("percent recomputes, every identity each statement states about itself holds, and")
    print("every printed row is reached by one of them.")
    if n:
        print(f'{n} printed defect{"" if n == 1 else "s"} noted above: the town\'s own '
              f'pages disagreeing with')
        print('themselves or with each other, pinned to the penny and not adjusted away.')
    print('This is CABLE FRANCHISE money. None of it is a tax dollar and none of it is')
    print('available to the general fund.')


if __name__ == '__main__':
    main()
