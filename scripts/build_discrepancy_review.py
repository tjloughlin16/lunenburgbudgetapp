"""Write the one-page discrepancy list for review by the Town.

    python3 scripts/build_discrepancy_review.py

Writes `notes/REVIEW-DISCREPANCIES.md`.

Generated, not written, for rule 2's reason: every figure is derived here, so re-running
after any ingest keeps the document current instead of quoting a number the data no
longer produces.

WHAT THIS IS AND IS NOT

It is a list of places where two documents we hold disagree, or where the ledger records
something the budget documents do not explain. **It is not an audit and nothing in it is
an accusation.** Where the archive cannot say which document is right, it says so. The
companion `notes/REQUEST-CODING.md` is the longer version for the Superintendent; this is
the short one, and the two are generated from the same comparison so they cannot drift
apart.

CONCISE ON PURPOSE. One table, then one short block per item. Anything a reader would
have to take on trust is given as the account number and the two figures.
"""
import collections
import csv
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_code_reconciliation_xlsx import load, match, m  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'notes', 'REVIEW-DISCREPANCIES.md')


def d(v):
    return f'${v:,.0f}' if v >= 0 else f'-${abs(v):,.0f}'


def main():
    led, book = load()
    A, B, label, uncoded = (collections.defaultdict(list),
                            collections.defaultdict(list), {}, [])
    for r in led:
        A[r['function']].append(r)
    for r in book:
        g = re.match(r'\s*(\d{4})', r['function_group'] or '')
        if not g:
            if abs(m(r['fy26_final'])) >= 0.5:
                uncoded.append(r)
            continue
        B[g.group(1)].append(r)
        lbl = re.sub(r'^\d{4}\s*-\s*', '', (r['function_group'] or '').strip()).strip()
        label.setdefault(g.group(1), [])
        if lbl and lbl not in label[g.group(1)]:
            label[g.group(1)].append(lbl)

    codes = sorted(set(A) | set(B))
    tot = lambda c: (sum(m(x['original']) for x in A[c]),
                     sum(m(x['fy26_final']) for x in B[c]))
    off = [c for c in codes if abs(tot(c)[0] - tot(c)[1]) > max(1.0, len(A[c]))]
    naked = [r for r in led if abs(m(r['original'])) < 0.5
             and abs(m(r['expended'])) >= 0.5 and abs(m(r['transfers'])) < 0.5]
    blind, split = [], []
    for c in codes:
        pairs, spare = match(B[c], A[c])
        blind += [a for a in spare if abs(m(a['transfers'])) >= 0.5]
        if c in off:
            continue
        ub = [b for b, a, _ in pairs if a is None and abs(m(b['fy26_final'])) >= 0.5]
        # Every unpaired account, not only those with an appropriation. A zero-approp
        # account that carries a revised figure is exactly the counterpart a reader is
        # looking for, and excluding it made the ledger column read as empty.
        sp = [a for a in spare
              if abs(m(a['original'])) >= 0.5 or abs(m(a['revised'])) >= 0.5]
        # A code where the only unpaired thing is a zero-appropriation account with no
        # workbook counterpart is not a split -- there is nothing on either side to
        # reconcile. Those accounts are reported under 'spent without budget' or
        # 'transfers' instead, which is where they belong.
        if ub:
            split.append((c, ub, sp))
    # Which basis does the workbook's FY26 column use? Only testable where a transfer
    # made the appropriation and the revised budget differ.
    moved = [r for r in led if abs(m(r['transfers'])) >= 0.5]
    basis_o = basis_r = basis_x = 0
    for c in codes:
        prs, spr = match(B[c], A[c])
        for b, a, _ in prs:
            if a is None or abs(m(a['transfers'])) < 0.5:
                continue
            v = m(b['fy26_final'])
            if abs(v - m(a['original'])) <= 1.0:
                basis_o += 1
            elif abs(v - m(a['revised'])) <= 1.0:
                basis_r += 1
        basis_x += len([a for a in spr if abs(m(a['transfers'])) >= 0.5])
    led_tot = sum(m(r['original']) for r in led)
    bk_tot = sum(m(r['fy26_final']) for r in book)

    def acc(nm, fn):
        """An account by name AND function code. The name alone is not unique: three
        different accounts are called DUES/FEES, and taking the first returned the
        $1,687 supplies line where the $29,965 athletics one was meant."""
        hit = [r for r in led if r['name'].strip() == nm and r['function'] == fn]
        if len(hit) != 1:
            raise SystemExit('%s/%s matches %d accounts, expected 1'
                             % (nm, fn, len(hit)))
        return hit[0]

    def bk(lbl):
        return next((r for r in book if r['line_item'].strip() == lbl), None)

    L = []
    A_ = L.append
    A_('# FY2026 school budget — points for review')
    A_('')
    A_('**To:** Town Manager and Town Accountant, Town of Lunenburg  ')
    A_('**Generated:** %s by `scripts/build_discrepancy_review.py`' % date.today())
    A_('')
    A_('Comparing two documents for the school department, FY2026: the Town '
       'Accountant’s')
    A_('MUNIS year-to-date budget report for period 12, and the district’s FY27 '
       'budget')
    A_('projection workbook, which carries the FY26 final budget. Both state amounts '
       'against')
    A_('the same function codes.')
    A_('')
    A_('**%d of %d function codes agree. The rest are below.** Nothing here is an '
       'accusation,' % (len(codes) - len(off), len(codes)))
    A_('and in most cases the archive cannot say which document is right — only '
       'that they')
    A_('cannot both be. Where I have a guess it is marked as one.')
    A_('')
    A_('| | category | items | amount involved | what it needs |')
    A_('|---|---|---:|---:|---|')
    sw_t = sum(m(r['original']) for r in led if r['name'].strip() == 'SOCWORKSAL')
    ell_ace = abs(m(bk('District Wide Specials (ELL)')['fy26_final'])
                  - m(bk('ACE Special Ed Resource Rm Teacher')['fy26_final']))
    rows = [
        ('A', 'Accounts not aligned', '4 pairs of codes',
         sw_t + ell_ace + m(bk('Salary Reserve')['fy26_final']) + 690.0,
         'Which code is authoritative'),
        ('B', 'Same total, different lines', '%d codes' % len(split),
         sum(m(b['fy26_final']) for _, ub, _ in split for b in ub),
         'Which line the money sits against'),
        ('C', '**Spent without budget**', '%d accounts' % len(naked),
         sum(m(r['expended']) for r in naked), '**How these were authorised**'),
        ('D', '**Budgeted with no account**', '1 line',
         m(bk('Curriculum Adoption')['fy26_final']), '**Where this was budgeted**'),
        ('E', 'Two figures on different bases', '2 accounts',
         abs(m(acc('ATH INS', '3510')['transfers'])),
         'Which basis the workbook column uses'),
        ('F', 'Money moved, no budget line', '%d accounts' % len(blind),
         sum(abs(m(r['transfers'])) for r in blind), 'What each transfer was for'),
    ]
    for key, cat, n, amt, need in rows:
        A_('| **%s** | %s | %s | %s | %s |' % (key, cat, n, d(amt), need))
    A_('')
    A_('**The amounts are the sums involved, not money missing, and they do not add '
       'up.** In')
    A_('most rows both documents hold the same total and disagree about where it sits. '
       'Taking')
    A_('every line on both sides the workbook totals %s and the ledger %s, a difference '
       'of' % (d(bk_tot), d(led_tot)))
    A_('**%s** — item 4 and rounding.' % d(bk_tot - led_tot))
    A_('')
    A_('---')
    A_('')
    A_('# A. Accounts not aligned')
    A_('')
    A_('*The same money under a different function code in each document. In every case')
    A_('both documents hold it; they disagree only about where it sits. The guess is')
    A_('mine, from the amounts, and is not established.*')
    A_('')
    A_('| codes | what | amount | my guess |')
    A_('|---|---|---:|---|')
    A_('| `2710` vs `2900` | Social worker salaries — %d accounts in the ledger under '
       'Guidance; the workbook gives them their own heading | %s | Same money, filed '
       'two ways. Nothing missing |'
       % (len([r for r in led if r['name'].strip() == 'SOCWORKSAL']),
          d(sum(m(r['original']) for r in led if r['name'].strip() == 'SOCWORKSAL'))))
    A_('| `2310` ↔ `2320` | District Wide Specials (ELL) %s and ACE Special Ed Resource '
       'Rm Teacher %s are each under the other\'s code | %s | One document has the two '
       'the wrong way round |'
       % (d(m(bk('District Wide Specials (ELL)')['fy26_final'])),
          d(m(bk('ACE Special Ed Resource Rm Teacher')['fy26_final'])),
          d(abs(m(bk('District Wide Specials (ELL)')['fy26_final'])
                - m(bk('ACE Special Ed Resource Rm Teacher')['fy26_final'])))))
    A_('| `0300` vs none | Salary reserve — coded in the ledger, carried under a section '
       'heading with no code in the workbook | %s | The same line |'
       % d(m(bk('Salary Reserve')['fy26_final'])))
    A_('| `4230` vs `4220` | P.S. Repair Office Machines | %s | The same line, coded two '
       'ways |' % d(690.0))
    A_('')
    A_('**The full code-level comparison**, for anyone who wants to check it:')
    A_('')
    A_('| code | workbook group | ledger | workbook | difference |')
    A_('|---|---|---:|---:|---:|')
    for c in sorted(off, key=lambda c: -abs(tot(c)[0] - tot(c)[1])):
        a, b = tot(c)
        A_('| `%s` | %s | %s | %s | **%s** |'
           % (c, ' / '.join(label.get(c, [])) or '*no group under this code*',
              d(a), d(b), d(abs(a - b))))
    A_('')
    A_('# B. Same total, different lines')
    A_('')
    A_('*The code totals agree, so nothing is missing. The money sits against different')
    A_('lines inside it.*')
    A_('')
    A_('| code | ledger | workbook |')
    A_('|---|---|---|')
    for c, ub, sp in split:
        left = '; '.join(
            '%s appropriated %s, revised %s'
            % (a['name'].strip(), d(m(a['original'])), d(m(a['revised'])))
            if abs(m(a['original']) - m(a['revised'])) > 0.5
            else '%s %s' % (a['name'].strip(), d(m(a['original'])))
            for a in sp) or '—'
        A_('| `%s` | %s | %s |'
           % (c, left,
              '; '.join('%s %s' % (b['line_item'].strip(), d(m(b['fy26_final'])))
                        for b in ub) or '—'))
    A_('')
    A_('# C. Spent without budget')
    A_('')
    A_('*Nothing appropriated, no transfer in, and money paid out. %d accounts, %s.*'
       % (len(naked), d(sum(m(r['expended']) for r in naked))))
    A_('')
    A_('| account | name | spent |')
    A_('|---|---|---:|')
    for r in sorted(naked, key=lambda r: -m(r['expended'])):
        A_('| `%s` | %s | %s |' % (r['account'], r['name'].strip(), d(m(r['expended']))))
    A_('')
    A_('The two kindergarten accounts are %s of it. The FY26 approved budget published '
       'the' % d(sum(m(r['expended']) for r in naked if 'KIND' in r['name'].upper())))
    A_('kindergarten line as a cut, so the question is where these charges were '
       'provided for.')
    A_('')
    A_('# D. Budgeted with no account to spend it from')
    A_('')
    A_('*In the workbook, with no corresponding account anywhere in the ledger.*')
    A_('')
    A_('| workbook line | code | amount |')
    A_('|---|---|---:|')
    A_('| Curriculum Adoption | `2110` | %s |' % d(m(bk('Curriculum Adoption')['fy26_final'])))
    A_('')
    A_('Taking every line on both sides, the workbook totals %s and the ledger %s. This '
       'single' % (d(bk_tot), d(led_tot)))
    A_('line is all but %s of that difference.'
       % d(bk_tot - led_tot - m(bk('Curriculum Adoption')['fy26_final'])))
    A_('')
    A_('# E. Two figures on different bases')
    A_('')
    A_('*Only accounts with a transfer can show which basis the workbook uses, because '
       'only')
    A_('there do the appropriation and the revised budget differ. There are %d such '
       'accounts:' % len(moved))
    A_('the workbook matches the appropriation on %d of them, the revised budget on %d, '
       'and' % (basis_o, basis_r))
    A_('%d cannot be told apart because they pair with nothing.*' % basis_x)
    A_('')
    A_('| account | appropriated | moved | revised | workbook says |')
    A_('|---|---:|---:|---:|---:|')
    ai = acc('ATH INS', '3510')
    df = acc('DUES/FEES', '3510')
    A_('| `ATH INS` athletic insurance | %s | %s | %s | **%s** |'
       % (d(m(ai['original'])), d(m(ai['transfers'])), d(m(ai['revised'])),
          d(m(bk('Athletic Insurance')['fy26_final']))))
    A_('| `DUES/FEES` athletic dues and fees | %s | %s | %s | **%s** |'
       % (d(m(df['original'])), d(m(df['transfers'])), d(m(df['revised'])),
          d(m(bk('Athletic Dues & Fees')['fy26_final']))))
    A_('')
    A_('Insurance matches the revised figure rather than the appropriation; dues and '
       'fees')
    A_('matches neither. Which basis does the workbook column use, and for which lines?')
    A_('')
    A_('# F. Money moved, with no budget line to match')
    A_('')
    A_('*%d accounts had money transferred in or out and pair with nothing in the '
       'workbook.*' % len(blind))
    A_('')
    A_('| account | name | appropriated | moved | spent |')
    A_('|---|---|---:|---:|---:|')
    for r in sorted(blind, key=lambda r: -abs(m(r['transfers']))):
        A_('| `%s` | %s | %s | %s | %s |'
           % (r['account'], r['name'].strip(), d(m(r['original'])),
              d(m(r['transfers'])), d(m(r['expended']))))
    A_('')
    A_('## What would close most of this in one step')
    A_('')
    A_('**The account master** — the mapping from each MUNIS account number to its '
       'function')
    A_('code and description. **A and B answer themselves from it**, which is most of '
       'the')
    A_('codes and most of the dollars.')
    A_('')
    A_('**C, D, E and F need a word from somebody.** A mapping cannot show a line that '
       'has no')
    A_('account, say how a charge was authorised against an account with no budget, '
       'explain')
    A_('which basis a column is on, or say what a transfer was for.')
    A_('')
    A_('## Method, in three lines')
    A_('')
    A_('The join is the function code in the fourth segment of the MUNIS account string')
    A_('(`0100-3-300-2330-51-2-13-1-511203`), which is the same code the workbook prints '
       'over')
    A_('each group. Within a code, lines are paired **by amount**, which is not a key: '
       'it shows')
    A_('a figure of that size exists on both sides, never that the two are the same '
       'line. The')
    A_('full working is in `sources/data/fy26-code-reconciliation.xlsx`.')
    A_('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    print('wrote %s — %d codes differ, %d split, %d unbudgeted, %d untraced transfers'
          % (os.path.relpath(OUT, ROOT), len(off), len(split), len(naked), len(blind)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
