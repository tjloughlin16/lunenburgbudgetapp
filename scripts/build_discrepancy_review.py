"""Write the categorised discrepancy list for review by the Town.

    python3 scripts/build_discrepancy_review.py

Writes `notes/REVIEW-DISCREPANCIES.md`.

Generated, not written, for rule 2's reason: every figure is derived here, so re-running
after any ingest keeps the document current instead of quoting a number the data no
longer produces.

THREE THINGS THIS FILE IS CAREFUL ABOUT

1.  **Every row carries a locator on BOTH sides.** The ledger account number, and the
    workbook's own row number and printed line name. A reader must be able to open each
    document and land on the row, not go searching for it. That is also what makes a
    disagreement checkable rather than something to take on trust.

2.  **Every account has exactly ONE category.** Athletics dues appeared in three at once
    -- the same account counted three times, inflating two totals. Category E owns the
    two accounts whose workbook figure is not their appropriation; B and F exclude them.

3.  **Categories are ordered by what needs an answer, not by dollar size.** The largest
    number here is a classification question where both documents hold the money and
    nothing is missing. The smallest is $1,896 of instructional materials. Sorting by
    amount would put the benign item first and the control question fourth.

Nothing here is an accusation, and where the archive cannot say which document is right
it says so. The companion `notes/REQUEST-CODING.md` is the longer version for the
Superintendent; both are generated from the same comparison so they cannot drift apart.
"""
import collections
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_code_reconciliation_xlsx import load, match, m  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'notes', 'REVIEW-DISCREPANCIES.md')

# Named for what each document IS to the reader, not for what it is to this project.
# "the ledger" and "the workbook" are our words; a Town Manager reads a year-to-date
# report and a school budget.
YTD_FILE = 'FY26 BUDGET YEAR TO DATE REPORT (9-1-2026).xlsx'
YTD_WHERE = 'sheet `ACCOUNT DETAIL`, column E'
BUD_FILE = 'FY27 budget projection workbook, FY26 FINAL BUDGET column'
BUD_WHERE = 'sheet `FY27 Budget Projection`, column B'


def d(v):
    return f'${v:,.0f}' if v >= 0 else f'-${abs(v):,.0f}'


def main():
    led, book = load()

    def acc(nm, fn):
        """An account by name AND function code. The name alone is not unique: three
        accounts are called DUES/FEES, and taking the first returned the $1,687 supplies
        line where the $29,965 athletics one was meant."""
        hit = [r for r in led if r['name'].strip() == nm and r['function'] == fn]
        if len(hit) != 1:
            raise SystemExit('%s/%s matches %d accounts, expected 1' % (nm, fn, len(hit)))
        return hit[0]

    def bk(lbl):
        hit = [r for r in book if r['line_item'].strip() == lbl]
        if len(hit) != 1:
            raise SystemExit('workbook line %r matches %d rows, expected 1'
                             % (lbl, len(hit)))
        return hit[0]

    def brow(lbl):
        """The workbook's own row number, so nobody has to search for the line."""
        return 'row %s' % bk(lbl)['row']

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

    def tot(c):
        return (sum(m(x['original']) for x in A[c]),
                sum(m(x['fy26_final']) for x in B[c]))

    off = [c for c in codes if abs(tot(c)[0] - tot(c)[1]) > max(1.0, len(A[c]))]
    naked = [r for r in led if abs(m(r['original'])) < 0.5
             and abs(m(r['expended'])) >= 0.5 and abs(m(r['transfers'])) < 0.5]

    # E owns these two; B and F exclude them so no account is counted twice.
    basis = [(acc('ATH INS', '3510'), bk('Athletic Insurance')),
             (acc('DUES/FEES', '3510'), bk('Athletic Dues & Fees'))]
    owned_a = {r['account'] for r, _ in basis}
    # Category D owns these two: both have an appropriation AND a school budget line, so
    # neither belongs in a category about accounts with nothing appropriated. They were
    # in both, which double-counted $91,460.
    owned_a |= {acc('SCHSALRESE', '0300')['account'], acc('REP OFF MA', '4230')['account']}
    owned_b = {r['line_item'].strip() for _, r in basis}

    blind, split = [], []
    for c in codes:
        pairs, spare = match(B[c], A[c])
        blind += [a for a in spare
                  if abs(m(a['transfers'])) >= 0.5 and a['account'] not in owned_a]
        if c in off:
            continue
        ub = [b for b, a, _ in pairs if a is None and abs(m(b['fy26_final'])) >= 0.5
              and b['line_item'].strip() not in owned_b]
        sp = [a for a in spare
              if (abs(m(a['original'])) >= 0.5 or abs(m(a['revised'])) >= 0.5)
              and a['account'] not in owned_a]
        if ub:
            split.append((c, ub, sp))

    # Which basis is the workbook's FY26 column on? Only testable where a transfer made
    # the appropriation and the revised budget differ.
    moved = [r for r in led if abs(m(r['transfers'])) >= 0.5]
    bo = br = bx = 0
    for c in codes:
        prs, spr = match(B[c], A[c])
        for b, a, _ in prs:
            if a is None or abs(m(a['transfers'])) < 0.5:
                continue
            v = m(b['fy26_final'])
            if abs(v - m(a['original'])) <= 1.0:
                bo += 1
            elif abs(v - m(a['revised'])) <= 1.0:
                br += 1
        bx += len([a for a in spr if abs(m(a['transfers'])) >= 0.5])

    led_tot = sum(m(r['original']) for r in led)
    bk_tot = sum(m(r['fy26_final']) for r in book)
    sw = [r for r in led if r['name'].strip() == 'SOCWORKSAL']
    ell, ace = bk('District Wide Specials (ELL)'), bk('ACE Special Ed Resource Rm Teacher')
    ca, sr = bk('Curriculum Adoption'), bk('Salary Reserve')
    rom = acc('REP OFF MA', '4230')

    L = []
    P = L.append
    P('# FY2026 school budget — points for review')
    P('')
    P('**To:** Town Manager and Town Accountant, Town of Lunenburg  ')
    P('**Generated:** %s by `scripts/build_discrepancy_review.py`' % date.today())
    P('')
    P('Comparing two documents for the school department, FY2026:')
    P('')
    P('- **the YTD report** — the Town Accountant’s `%s`, %s' % (YTD_FILE, YTD_WHERE))
    P('- **the school budget** — the district’s %s, %s' % (BUD_FILE, BUD_WHERE))
    P('')
    P('Both state amounts against the same function codes. **%d of %d codes agree.**'
      % (len(codes) - len(off), len(codes)))
    P('')
    P('Every item below gives the account number and the school budget row, so each one')
    P('can be opened in both documents without searching. Nothing here is an accusation, and in')
    P('most cases the archive cannot say which document is right — only that they cannot')
    P('both be. Where I have a guess it is marked as one.')
    P('')
    P('**Ordered by what needs an answer, not by size.** The largest amount is a')
    P('classification question where both documents hold the money; the smallest is')
    P('$1,896 of instructional materials.')
    P('')
    P('| | category | items | sum involved | what it needs |')
    P('|---|---|---:|---:|---|')
    cats = [
        ('A', '**Spent without budget**', '%d accounts' % len(naked),
         sum(m(r['expended']) for r in naked), '**How these were authorised**'),
        ('B', '**Budgeted with no account to spend from**', '1 line',
         m(ca['fy26_final']), '**Where this was budgeted**'),
        ('C', 'Nothing appropriated, funded by transfer', '%d accounts' % len(blind),
         sum(abs(m(r['transfers'])) for r in blind), 'What each transfer paid for'),
        ('D', 'Accounts not aligned', '4 pairs of codes',
         sum(m(r['original']) for r in sw) + abs(m(ell['fy26_final'])
                                                 - m(ace['fy26_final']))
         + m(sr['fy26_final']) + m(rom['original']),
         'Which code is authoritative'),
        ('E', 'Two figures on different bases', '2 accounts',
         abs(m(basis[0][0]['transfers'])), 'Which basis the school budget column uses'),
        ('F', 'Same total, different lines', '%d code' % len(split),
         sum(m(b['fy26_final']) for _, ub, _ in split for b in ub),
         'Which line the money sits against'),
    ]
    for k, cat, n, amt, need in cats:
        P('| **%s** | %s | %s | %s | %s |' % (k, cat, n, d(amt), need))
    P('')
    P('**The sums are the amounts involved, not money missing, and they do not add up.**')
    P('In D and F both documents hold the same total and disagree only about where it')
    P('sits.')
    P('')
    P('---')
    P('')
    P('# A. Spent without budget')
    P('')
    P('*Nothing appropriated, no transfer in, and money paid out. %d accounts, %s.*'
      % (len(naked), d(sum(m(r['expended']) for r in naked))))
    P('')
    P('| YTD report account | name | spent | in the school budget |')
    P('|---|---|---:|---|')
    for r in sorted(naked, key=lambda r: -m(r['expended'])):
        # NOT 'no line carries this'. The workbook does carry lines under these codes --
        # Kindergarten Aides/Regular is printed at $0 -- they simply have no amount. Which
        # blank line corresponds to which account is a name judgement, so the count and
        # the code are given and the reader decides.
        blanks = [b for b in B[r['function']] if abs(m(b['fy26_final'])) < 0.5]
        P('| `%s` | %s | %s | code `%s` — %d line%s under it, none with an amount |'
          % (r['account'], r['name'].strip(), d(m(r['expended'])), r['function'],
             len(blanks), '' if len(blanks) == 1 else 's'))
    P('')
    P('The two kindergarten accounts are %s of it. The FY26 approved budget published the'
      % d(sum(m(r['expended']) for r in naked if 'KIND' in r['name'].upper())))
    P('kindergarten line as a cut, so the question is where these charges were provided')
    P('for. The school budget does carry a **Kindergarten Aides/Regular** line, %s,'
      % brow('Kindergarten Aides/Regular'))
    P('printed at $0, and a **Kindergarten Paraprofessionals** line, %s, left blank.'
      % brow('Kindergarten Paraprofessionals'))
    P('')
    P('# B. Budgeted with no account to spend from')
    P('')
    P('*In the school budget, with no corresponding account anywhere in the YTD report.*')
    P('')
    P('| school budget | code | amount | YTD report |')
    P('|---|---|---:|---|')
    P('| **Curriculum Adoption** — %s | `2110` | %s | no account of any amount |'
      % (brow('Curriculum Adoption'), d(m(ca['fy26_final']))))
    P('')
    P('Taking every line on both sides, the school budget totals %s and the YTD report '
      '%s. This'
      % (d(bk_tot), d(led_tot)))
    P('single line is all but %s of that difference.'
      % d(bk_tot - led_tot - m(ca['fy26_final'])))
    P('')
    P('# C. Nothing appropriated, funded entirely by transfer')
    P('')
    P('*The school budget appropriates **nothing** to these %d accounts. Each was given'
      % len(blind))
    P('money by transfer during the year. One is nearly all of it.*')
    P('')
    P('| YTD report account | name | appropriated | moved | spent |')
    P('|---|---|---:|---:|---:|')
    for r in sorted(blind, key=lambda r: -abs(m(r['transfers']))):
        P('| `%s` | %s | %s | %s | %s |'
          % (r['account'], r['name'].strip(), d(m(r['original'])),
             d(m(r['transfers'])), d(m(r['expended']))))
    P('')
    P('# D. Accounts not aligned')
    P('')
    P('*The same money under a different function code in each document. Both documents')
    P('hold it; they disagree only about where it sits. The guess is mine, from the')
    P('amounts, and is not established.*')
    P('')
    P('| codes | in the YTD report | in the school budget | amount | my guess |')
    P('|---|---|---|---:|---|')
    P('| `2710` vs `2900` | %s | %s | %s | Same money, filed two ways. Nothing missing |'
      % ('; '.join('`%s`' % r['account'] for r in sorted(sw, key=lambda r: r['account'])),
         '; '.join('%s %s' % (lbl, brow(lbl)) for lbl in
                   ('P.S. Social Worker', 'E.S. Social Worker', 'M.S Social Worker',
                    'H.S. Social Worker')),
         d(sum(m(r['original']) for r in sw))))
    P('| `2310` ↔ `2320` | `%s` DWSPECIALI and `%s` ACERESROOM | District Wide Specials '
      '(ELL) %s and ACE Special Ed Resource Rm Teacher %s | %s | One document has the two '
      'the wrong way round |'
      % (acc('DWSPECIALI', '2310')['account'], acc('ACERESROOM', '2320')['account'],
         brow('District Wide Specials (ELL)'),
         brow('ACE Special Ed Resource Rm Teacher'),
         d(abs(m(ell['fy26_final']) - m(ace['fy26_final'])))))
    P('| `0300` vs none | `%s` SCHSALRESE | Salary Reserve, %s — under a section heading '
      'with no code | %s | The same line |'
      % (acc('SCHSALRESE', '0300')['account'], brow('Salary Reserve'),
         d(m(sr['fy26_final']))))
    P('| `4230` vs `4220` | `%s` REP OFF MA | P.S. Repair Office Machines, %s | %s | The '
      'same line, coded two ways |'
      % (rom['account'], brow('P.S. Repair Office Machines'), d(m(rom['original']))))
    P('')
    P('**The full code comparison**, for anyone checking:')
    P('')
    P('| code | school budget group | YTD report | school budget | difference |')
    P('|---|---|---:|---:|---:|')
    for c in sorted(off, key=lambda c: -abs(tot(c)[0] - tot(c)[1])):
        a, b = tot(c)
        P('| `%s` | %s | %s | %s | **%s** |'
          % (c, ' / '.join(label.get(c, [])) or '*no group under this code*',
             d(a), d(b), d(abs(a - b))))
    P('')
    P('# E. Two figures on different bases')
    P('')
    P('*Only accounts with a transfer can show which basis the school budget uses,')
    P('because only there do the appropriation and the revised budget differ.')
    P('There are %d such accounts: the school budget matches the appropriation on %d,'
      % (len(moved), bo))
    P('the revised budget on %d, and %d cannot be told apart.*' % (br, bx))
    P('')
    P('| YTD report account | appropriated | moved | revised | school budget says | school budget line |')
    P('|---|---:|---:|---:|---:|---|')
    for a, b in basis:
        P('| `%s` %s | %s | %s | %s | **%s** | %s, %s |'
          % (a['account'], a['name'].strip(), d(m(a['original'])), d(m(a['transfers'])),
             d(m(a['revised'])), d(m(b['fy26_final'])), b['line_item'].strip(),
             brow(b['line_item'].strip())))
    P('')
    P('Insurance matches the revised figure rather than the appropriation; dues and fees')
    P('matches neither. Which basis does the school budget column use, and for which lines?')
    P('')
    P('# F. Same total, different lines')
    P('')
    P('*The code total agrees, so nothing is missing and no dollar is unaccounted for.')
    P('The money sits against different lines inside the code — which is what happens')
    P('when one account covers what the school budget splits across schools.*')
    P('')
    P('| code | YTD report | school budget |')
    P('|---|---|---|')
    for c, ub, sp in split:
        left = '; '.join('`%s` %s %s' % (a['account'], a['name'].strip(),
                                         d(m(a['original']))) for a in sp) or '—'
        P('| `%s` | %s | %s |'
          % (c, left,
             '; '.join('%s %s, %s' % (b['line_item'].strip(), d(m(b['fy26_final'])),
                                      brow(b['line_item'].strip())) for b in ub) or '—'))
    P('')
    P('## What would close most of this in one step')
    P('')
    P('**The account master** — the mapping from each MUNIS account number to its')
    P('function code and description. **D and F answer themselves from it.**')
    P('')
    P('**A, B, C and E need a word from somebody.** A mapping cannot say how a charge was')
    P('authorised against an account with no budget, show a budget line that has no')
    P('account, say what a transfer paid for, or explain which basis a column is on.')
    P('')
    P('## Method, in four lines')
    P('')
    P('The join is the function code in the fourth segment of the MUNIS account string')
    P('(`0100-3-300-2330-51-2-13-1-511203`), which is the same code the school budget')
    P('prints over each group. Within a code, lines are paired **by amount**, which is not a')
    P('key: it shows a figure of that size exists on both sides, never that the two are')
    P('the same line. Full working in `sources/data/fy26-code-reconciliation.xlsx`.')
    P('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  A %d unbudgeted  B 1 no-account  C %d transfers  D %d codes  E 2 bases  '
          'F %d split' % (len(naked), len(blind), len(off), len(split)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
