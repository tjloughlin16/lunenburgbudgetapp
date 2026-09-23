#!/usr/bin/env python3
"""The PEG access fund's own accounts, FY2015 to FY2025, from the annual town reports.

Lunenburg's Public, Educational and Governmental access committee runs on cable revenue
paid by Comcast into an enterprise fund, not on the tax levy. It publishes its own small
set of accounts inside the annual report every year: what came in, what went out, and the
expense lines as a percentage of the whole.

**Nothing in this archive held any of it**, and the pages were in the reading queue under
two different wrong subjects -- three as `enrollment` and one as `payroll`, because the
classifier saw `Salaries` and a percentage. Rule 11's point in miniature: this is real
money paying real staff, appearing in no budget line, and the general fund appropriation
cannot see it.

Two tables, and each states an identity that proves it:

* `line_items` -- `Line Item | Expenses | % of Expense`, ending in a printed `Total` and a
  printed `100.00%`. Both columns are footed, and every row's percentage is recomputed
  from its own figure.
* `revenue_expenses` -- the block above it. `Revenue Total` is the sum of the receipts
  above it, and `TOTAL` is that less `Expenses`. The labels say so; this checks it.

The two tables are also checked against each other: `Expenses` in the revenue block is the
same quantity as `Total` at the foot of the line items, printed twice in different places
on the same page.

    python3 scripts/extract_peg_fund.py
    python3 scripts/extract_peg_fund.py --check
"""

import argparse
import collections
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_valuation import pages_of, text_of, num  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'peg-access-fund.csv')

# `report_fy` and `page` are the join keys `map_annual_report_pages.py` reads to mark a
# queued page read.
FIELDS = ['dataset', 'edition', 'report_fy', 'document', 'page', 'table', 'label', 'kind',
          'amount', 'share_percent', 'columns_as_printed', 'status', 'reconciliation']

# Five headings for one table in eleven years: `Line Item Amount`, `Line Item
# Expenses % of Expense`, and the same with the `% of` wrapped onto the line above.
HEAD_ITEMS = re.compile(r'Line\s*Items?\s+(Expenses|Amount)', re.I)
HEAD_REV = re.compile(r'REVENUE\s*(vs|VS)\.?\s*EXPENSES', re.I)
MONEY = re.compile(r'^\(?[$S]?-?[\d][\d,.]*\)?$')
PCT = re.compile(r'^-?[\d][\d,.]*%$')

RECEIPT = re.compile(r'^(Starting Balance|Revenue|Enterprise Interest|Grant|'
                     r'Capital Infusion)', re.I)


def token(w):
    """One OCR box as a figure-shaped string, with the rules' own debris removed.

    The FY2022 table prints a rule between the label and the figure and the OCR keeps it
    inside the box: `| $11,446.21`. Read literally that is not a number, the row is
    dropped, and the expense column comes out $11,446.21 short against its own printed
    total -- which is what happened, and is exactly the silent shortfall this whole file
    exists to refuse.
    """
    return w['text'].strip().replace(' ', '').lstrip('|[').rstrip('|]')


def pieces(w):
    """One OCR box as the separate things printed in it.

    The boxes do not respect the columns. `Equip/maintenance | $11,446.21` is one box on
    the FY2022 page: a label, a rule and a figure. Splitting on whitespace and on the rule
    recovers all three; treating the box as one token loses the figure and the row with
    it. A lone `$` is glued back onto what follows it.
    """
    parts = [q for q in re.split(r'[\s|]+', w['text'].strip()) if q]
    out = []
    for q in parts:
        if out and out[-1] in ('$', 'S'):
            out[-1] = out[-1] + q
        else:
            out.append(q)
    return out


def figures(line):
    """The money and the percentage on a printed line, kept apart.

    A percentage and a dollar figure are different quantities and the page prints them in
    adjacent columns. Read as one list of numbers, `$51,146.74 40.21%` becomes two
    amounts, and the expense column then sums to something no reader could recognise.
    """
    amounts, pcts = [], []
    for w in line:
        for t in pieces(w):
            if PCT.match(t):
                v = num(t[:-1])
                if v is not None:
                    pcts.append(v)
            elif MONEY.match(t) and num(t) is not None and re.search(r'\d', t):
                amounts.append(num(t))
    return amounts, pcts


def label_of(line):
    out = []
    for w in line:
        stop = False
        for t in pieces(w):
            if PCT.match(t) or (MONEY.match(t) and num(t) is not None):
                stop = True
                break
            out.append(t)
        if stop:
            break
    return re.sub(r'\s+', ' ', ' '.join(out)).strip(' |')


def wrapped(lines, limit):
    """Rows, with a label that WRAPPED onto its own line joined back to its figure.

    `Purchase of` / `Services $1,134.00`, `Lease` / `$6,000.00`, `Revenue (from` /
    `Comcast) $180,792` -- the column is narrow and the labels are not. Read line by line
    those are two rows, one with no figure and one with half a name, and the half with the
    figure is what gets dropped: FY2019's expenses came out $13,260.24 short, which is
    exactly `Lease` plus `Insurance`.

    A short line carrying no figure is held and prepended to the next line that has one.
    A LONG one is prose and ends the table.
    """
    out, pending = [], ''
    for line in lines[:limit]:
        amounts, pcts = figures(line)
        label = label_of(line)
        if amounts:
            out.append(((pending + ' ' + label).strip(), amounts, pcts))
            pending = ''
            continue
        if label and len(label) <= 40 and not pcts:
            if out and pending:
                break
            pending = label
        elif out:
            break
    return out


def read_line_items(edition, doc, pages):
    for p, lines in sorted(pages.items()):
        idx = [i for i, line in enumerate(lines) if HEAD_ITEMS.search(text_of(line))]
        if not idx:
            continue
        head = text_of(lines[idx[0]]).strip()
        # FY2025 breaks the table across a page: the last expense line is the last thing
        # on page 64 and the `Total` is the first thing on page 65. Read to the end of
        # the page and stop, and that year has no total and cannot be checked -- so the
        # next page is offered to the same reader, and the total is found where it is.
        body = lines[idx[0] + 1:] + pages.get(p + 1, [])[:6]
        rows, total = [], None
        for label, amounts, pcts in wrapped(body, 34):
            if re.match(r'^totals?\b', label, re.I):
                total = (amounts[0], pcts[0] if pcts else None)
                break
            if not label:
                continue
            rows.append((label, amounts[0], pcts[0] if pcts else None))
        if len(rows) < 4 or total is None:
            continue
        return reconcile_items(edition, doc, p, head, rows, total)
    return []


def reconcile_items(edition, doc, page, head, rows, total):
    notes, ok = [], True
    got = sum(a for _, a, _ in rows)
    if abs(got - total[0]) < 0.02:
        notes.append(f'expenses: {got:,.2f} = the printed Total')
    else:
        notes.append(f'expenses: {got:,.2f} against a printed {total[0]:,.2f} '
                     f'({got - total[0]:+,.2f})')
        ok = False
    pcts = [q for _, _, q in rows if q is not None]
    if len(pcts) == len(rows):
        s = sum(pcts)
        if abs(s - 100) <= 0.06:
            notes.append(f'shares: the {len(rows)} lines sum to {s:.2f}%')
        else:
            notes.append(f'shares: the {len(rows)} lines sum to {s:.2f}%, not 100')
            ok = False
    elif not pcts:
        # `Line Item | Amount` is a real layout, printed for five years. A table that
        # prints no share column has not failed to print one.
        notes.append('shares: this layout prints no percentage column')
    else:
        notes.append(f'shares: {len(pcts)} of {len(rows)} lines printed one')
        ok = False
    bad = [lbl for lbl, a, q in rows
           if q is not None and total[0] and abs(a / total[0] * 100 - q) > 0.06]
    notes.append('each share is what its own figure gives' if not bad
                 else 'the printed share disagrees with the figure on: ' + ', '.join(bad))
    if bad:
        ok = False
    out = []
    for lbl, a, q in rows:
        out.append({'dataset': 'peg_access_fund', 'edition': edition, 'document': doc,
                    'page': page, 'table': 'line_items', 'label': lbl, 'kind': 'row',
                    'amount': a, 'share_percent': q, 'columns_as_printed': head,
                    'status': 'checked' if ok else 'check failed',
                    'reconciliation': ' ; '.join(notes)})
    out.append({'dataset': 'peg_access_fund', 'edition': edition, 'document': doc,
                'page': page, 'table': 'line_items', 'label': 'Total', 'kind': 'total',
                'amount': total[0], 'share_percent': total[1],
                'columns_as_printed': head,
                'status': 'checked' if ok else 'check failed',
                'reconciliation': ' ; '.join(notes)})
    return out


def read_revenue(edition, doc, pages):
    for p, lines in sorted(pages.items()):
        idx = [i for i, line in enumerate(lines) if HEAD_REV.search(text_of(line))]
        if not idx:
            continue
        head = text_of(lines[idx[0]]).strip()
        rows = []
        for label, amounts, _ in wrapped(lines[idx[0] + 1:], 14):
            if not label:
                continue
            rows.append((label, amounts[0]))
            if re.match(r'^total$', label, re.I):
                break
        if len(rows) < 4:
            continue
        return reconcile_revenue(edition, doc, p, head, rows)
    return []


def reconcile_revenue(edition, doc, page, head, rows):
    """`Revenue Total` is the receipts above it; `TOTAL` is that less `Expenses`.

    Both are identities the page's own labels assert, so neither is an assumption. The
    receipts that count toward `Revenue Total` differ by year -- FY2021 includes the
    starting balance in it and FY2022 prints no starting balance at all -- which is why
    the sum is taken over the rows the page actually printed above the line rather than
    over a fixed list of names.
    """
    # FIRST occurrence wins. The FY2020 block prints TWO lines called `Subtotal` --
    # 699,875.47, which is the receipts, and 449,041.36, which is something else the page
    # does not name -- and a plain dict keeps the second, so the receipts were reported
    # as $250,834.11 over their own subtotal.
    by = {}
    for lbl, v in rows:
        by.setdefault(lbl, v)
    notes, ok = [], True
    names = [lbl for lbl, _ in rows]
    # The same two lines are called four different things across eleven editions:
    # `Revenue Total` or `Subtotal`, and `TOTAL` or `Ending Balance`.
    sub = next((lbl for lbl, _ in rows
                if re.match(r'^(Revenue Total|Subtotal)$', lbl, re.I)), None)
    after = rows[[l for l, _ in rows].index(sub) + 1:] if sub else []
    close = next((lbl for lbl, _ in after
                  if re.match(r'^(TOTAL|Total|Ending Balance|Balance)$', lbl, re.I)
                  and lbl != sub), None)
    if sub:
        by['Revenue Total'] = by[sub]
    if close:
        by['__close__'] = next(v for lbl, v in after if lbl == close)
    if 'Revenue Total' in by:
        # Every row above the subtotal is a receipt, whatever it is called. Listing the
        # names instead missed `Enterprise Fund Interest` in FY2023 and FY2024 and
        # reported the receipts as short by exactly that line.
        above = []
        for lbl, v in rows:
            if lbl == sub:
                break
            above.append(v)
        got = sum(above)
        if abs(got - by['Revenue Total']) < 0.02:
            notes.append(f'Revenue Total: {got:,.2f} = the {len(above)} receipts above it')
        else:
            notes.append(f'Revenue Total: the {len(above)} receipts above it sum to '
                         f'{got:,.2f} against a printed {by["Revenue Total"]:,.2f} '
                         f'({got - by["Revenue Total"]:+,.2f})')
            ok = False
    else:
        notes.append('no Revenue Total printed')
        ok = False
    tot = by.get('__close__')
    if tot is not None and 'Revenue Total' in by and 'Expenses' in by:
        want = by['Revenue Total'] - by['Expenses']
        if abs(want - tot) < 0.02:
            notes.append(f'{close}: {tot:,.2f} = {sub} less Expenses')
        else:
            notes.append(f'{close}: {sub} less Expenses is {want:,.2f} against a '
                         f'printed {tot:,.2f} ({want - tot:+,.2f})')
            ok = False
    else:
        notes.append('a closing line, a subtotal and Expenses are not all printed: '
                     + ', '.join(names))
        ok = False
    return [{'dataset': 'peg_access_fund', 'edition': edition, 'document': doc,
             'page': page, 'table': 'revenue_expenses', 'label': lbl,
             'kind': 'total' if lbl in (sub, close) else 'row',
             'amount': v, 'share_percent': '', 'columns_as_printed': head,
             'status': 'checked' if ok else 'check failed',
             'reconciliation': ' ; '.join(notes)} for lbl, v in rows]


def cross_check(rows):
    """`Expenses` in the revenue block and `Total` at the foot of the line items are the
    same quantity, printed twice on one page."""
    by = collections.defaultdict(dict)
    for r in rows:
        if r['table'] == 'revenue_expenses' and r['label'] == 'Expenses':
            by[r['edition']]['revenue block'] = float(r['amount'])
        if r['table'] == 'line_items' and r['kind'] == 'total':
            by[r['edition']]['line items'] = float(r['amount'])
    out, agree = [], 0
    for ed in sorted(by):
        v = by[ed]
        if len(v) < 2:
            continue
        if abs(v['revenue block'] - v['line items']) < 0.02:
            agree += 1
        else:
            out.append(f'  !! {ed}: the revenue block says expenses of '
                       f'{v["revenue block"]:,.2f} and the line items foot to '
                       f'{v["line items"]:,.2f}')
    return [f'expenses stated twice on the page: {agree + len(out)} editions, '
            f'{agree} agree'] + out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rows = []
    for tsv in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        name = os.path.basename(tsv)
        m = re.search(r'fy-?(\d{4})', name)
        if not m:
            continue
        edition, doc = 'FY' + m.group(1), name.replace('.tsv', '.pdf')
        pages = pages_of(tsv)
        for reader in (read_revenue, read_line_items):
            for r in reader(edition, doc, pages):
                r['report_fy'] = m.group(1)
                rows.append({k: r.get(k, '') for k in FIELDS})

    rows.sort(key=lambda r: (r['edition'], r['table'], int(r['page'])))

    if args.check:
        if not os.path.exists(OUT):
            sys.exit(f'{OUT} does not exist')
        have = [dict(h) for h in csv.DictReader(open(OUT))]
        if have != [{k: ('' if v is None else str(v)) for k, v in r.items()}
                    for r in rows]:
            sys.exit(f'{OUT} is stale -- re-run scripts/extract_peg_fund.py')
        print(f'{OUT}: {len(rows)} rows, reproduces')
        return

    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    by = collections.defaultdict(list)
    for r in rows:
        by[(r['table'], r['edition'])].append(r)
    for table in ('revenue_expenses', 'line_items'):
        eds = [(e, rs) for (t, e), rs in sorted(by.items()) if t == table]
        ok = sum(1 for _, rs in eds if rs[0]['status'] == 'checked')
        print(f'{table}: {len(eds)} editions, {ok} checked, {len(eds) - ok} not')
        for e, rs in eds:
            mark = '  ' if rs[0]['status'] == 'checked' else '!!'
            print(f'  {mark} {e} p{int(rs[0]["page"]):>3} {len(rs):>2} rows  '
                  f'{rs[0]["reconciliation"][:120]}')
    print()
    for line in cross_check(rows):
        print(line)
    print(f'\nwrote {OUT}: {len(rows)} rows')


if __name__ == '__main__':
    main()
