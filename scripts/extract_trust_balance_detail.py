"""The annual report's TRUST FUND BALANCE DETAIL: every fund, by account, in one list.

    python3 scripts/extract_trust_balance_detail.py
    python3 scripts/extract_trust_balance_detail.py --check

Writes `sources/data/trust-fund-balances.csv`.

THE TABLE WE WERE NOT READING.

This project spent weeks on the annual report's `TRUST AND STABILIZATION FUNDS HELD BY
OTHER BANKS` pages -- a wide, skewed, multi-column table that has to be de-skewed, column
-clustered and proved against its own arithmetic, and which yields nothing at all in six
of fifteen years. Meanwhile the same reports print THIS: a plain list of every fund by
account number with its balance beside it, no layout to speak of, nothing to prove because
there is nothing to add up.

TJ found it in about a minute by searching the PDF for `8124`, the general Stabilization
Fund's account number, after saying: *"i can almost guarantee you this data is all in the
annual town report. you prob missed it."* He was right, and the reason the reader missed
it is worth keeping: the extractor was looking for a TABLE, and this is a LIST. Every
heuristic in `read_trust_table.py` -- six or more columns, an identity to close, a skew to
measure -- describes the hard table and disqualifies the easy one.

**It is also the COMPLETE one.** The other-banks table holds the funds at TD Banknorth,
Unibank and MMDT; the general Stabilization Fund is not on it, because it is held
elsewhere. This list has all of them.

WHAT PROVES IT, GIVEN THERE IS NO TOTAL TO FOOT

The page prints no grand total for the fund list, so rule 13's "reconcile to the source's
own total" has nothing to reconcile to. The check is stronger than a total anyway: **every
FY2025 balance here must equal the balance MUNIS prints for the same account**, and the
ledger is a different document produced by a different system. The extract refuses to
write unless they tie on every stabilization account; where an account outside that
group disagrees, the disagreement is RECORDED per row rather than suppressed. A layout error cannot survive that.

WHAT IT COVERS

Only FY2024 and FY2025 print this listing -- it arrives with a change in how the
Treasurer's section is laid out. That is two years, and it is two years for EVERY fund
rather than for the two or three whose arithmetic happened to close.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'trust-fund-balances.csv')
LEDGER = os.path.join(ROOT, 'sources', 'data', 'trust-agency-balances.csv')

# Trust and agency accounts: the 8000s are the funds, the 9000s the agency accounts the
# same listing carries.
# A LEADING CODE, NOT A LONE ONE. OCR returns the account number as its own observation
# on some rows and merged into the fund name on others -- `8136 Vehicle/Equipment
# Stabilization Fund - Expendable` is one box -- and an anchored pattern silently drops
# every merged row. That cost 33 of FY2024's 50 rows, including every stabilization fund
# on the page.
CODE = re.compile(r'^(8[01]\d\d|9\d{3})\b')
# `$ 2,254,933.99` as well as `2,254,933.99`: FY2024 prints the sign in the same
# observation and FY2025 does not, and a pattern that admits only one of them reads one
# year and silently skips the other.
MONEY = re.compile(r'^\$?\s*-?[\d,]{1,15}\.\d{2}$')

# A page is the listing if it carries this many accounts AND this many figures. Both
# halves matter: an index page names accounts and prints no money, and a narrative page
# prints money and names no accounts.
MIN_ACCOUNTS, MIN_FIGURES = 12, 12

# AND IT HAS TO SAY WHAT IT IS. Shape alone is not enough to identify this listing, and
# trusting shape published a wrong figure: FY2014's page 38 is the OTHER-BANKS table,
# which is also a grid of account numbers and money, and its leftmost money column is the
# BEGINNING principal rather than the balance. The extractor read $226,821.90 for the
# Zoning fund where the proven series has $227,201.90 -- the same fund, the same year, off
# by one column.
#
# Nothing but the heading distinguishes the two reliably, so the heading is required. It
# sits on the data page or the one before it, because the section runs across a spread.
HEADING = re.compile(r'trust\s+fund\s+balance', re.I)

FIELDS = ['fy', 'account', 'name', 'balance', 'ledger_balance', 'ledger_agrees',
          'page', 'document']

# The accounts MUNIS files under STABILIZATION FUNDS. A layout error would break these
# along with everything else, so they are what the extract refuses to write without.
STAB = ('8124', '8125', '8129', '8133', '8136', '8137', '8138', '8140', '8141')


def num(t):
    return float(t.replace('$', '').replace(',', '').strip())


def balance_column(boxes):
    """The x-range of the FUND BALANCE column, measured from the page.

    THE FIGURE NEAREST THE NAME IS NOT ALWAYS THE BALANCE. Taking the first figure to the
    right of the account number reads the balance on most rows and the RECEIPTS column on
    any row whose balance the scan dropped -- and it drops some: on FY2025 the Health
    Insurance and School Prize rows arrive with their receipts figure and no balance at
    all. That silently published $139.21 as a fund holding $11,026.88, and the only
    reason it was caught is that the ledger disagreed.

    So the column is bound by POSITION instead. Figures are right-aligned in an accounting
    printout, so their right edges cluster; the leftmost cluster is the balance, and every
    column after it is receipts, BANs or deficits. A row with nothing in that cluster
    yields no row at all, which is the same standard the rest of this archive keeps:
    publish what the page shows, omit what it does not.
    """
    rights = sorted(b['x'] + b.get('w', 0.0) for b in boxes
                    if MONEY.match((b['text'] or '').strip()))
    if not rights:
        return None
    groups, cur = [], [rights[0]]
    for lo, hi in zip(rights, rights[1:]):
        if hi - lo > 0.03:
            groups.append(cur); cur = [hi]
        else:
            cur.append(hi)
    groups.append(cur)
    # The leftmost group with enough members to be a column rather than a stray.
    for g in groups:
        if len(g) >= 5:
            return (min(g) - 0.02, max(g) + 0.02)
    return (min(groups[0]) - 0.02, max(groups[0]) + 0.02)


def rows_on(path, page, boxes):
    """One row per account: the code, the name beside it, the figure in the balance column."""
    span = balance_column(boxes)
    if not span:
        return []
    lo, hi = span
    out = []
    for c in [b for b in boxes if CODE.match((b['text'] or '').strip())]:
        near = [b for b in boxes if abs(b['y'] - c['y']) < 0.004 and b['x'] > c['x']]
        figs = [b for b in near
                if MONEY.match((b['text'] or '').strip())
                and lo <= b['x'] + b.get('w', 0.0) <= hi]
        if not figs:
            continue
        names = sorted([b for b in near
                        if not MONEY.match((b['text'] or '').strip())
                        and len((b['text'] or '').strip()) > 3], key=lambda b: b['x'])
        name = ' '.join((names[0]['text'] or '').split()) if names else ''
        if not name:
            t = (c['text'] or '').strip()
            name = ' '.join(t.split()[1:]) if len(t.split()) > 1 else ''
        out.append(dict(account=(c['text'] or '').strip().split()[0], name=name,
                        balance=num((figs[0]['text'] or '').strip()),
                        page=page, document=os.path.relpath(path, ROOT)))
    return out


def read_page(path):
    by_page = collections.defaultdict(list)
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            try:
                by_page[r['page']].append(dict(
                    x=float(r['x']), y=float(r['y']), w=float(r['w']),
                    text=r['text'] or ''))
            except (TypeError, ValueError):
                continue
    # THE SAME 180-DEGREE TURN THE OTHER READER HANDLES. FY2024's listing comes off the
    # scanner reversed -- fund names at high x, figures at low -- so "the figure to the
    # right of the account number" finds nothing and the year reads as absent. The
    # detector already exists; it is imported rather than rewritten.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from read_trust_table import upright
    except Exception:
        upright = lambda b: b
    by_page = {p: upright(b) for p, b in by_page.items()}
    titled = {p for p, bs in by_page.items()
              if any(HEADING.search(b['text'] or '') for b in bs)}
    # ...or the page after one that carries it.
    titled |= {str(int(p) + 1) for p in titled if str(int(p) + 1) in by_page}
    best = None
    for page, boxes in by_page.items():
        if page not in titled:
            continue
        na = sum(1 for b in boxes if CODE.match(b['text'].strip()))
        nf = sum(1 for b in boxes if MONEY.match(b['text'].strip()))
        if na >= MIN_ACCOUNTS and nf >= MIN_FIGURES and (best is None or na > best[1]):
            best = (page, na, boxes)
    if not best:
        return None, []
    page, _, boxes = best
    return page, rows_on(path, int(page), boxes)


def ledger():
    if not os.path.exists(LEDGER):
        return {}
    return {r['account']: float(r['held'])
            for r in csv.DictReader(open(LEDGER, encoding='utf-8'))
            if r.get('held')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    body, found = [], []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        page, rows = read_page(f)
        if not rows:
            continue
        found.append((fy, page, len(rows)))
        for r in rows:
            body.append(dict(fy=fy, **r))

    if not body:
        print('no annual report carries a per-account trust fund listing', file=sys.stderr)
        return 1

    # RECONCILE AGAINST A DIFFERENT DOCUMENT, because this page prints no total of its own.
    # The ledger's opening balance for FY2026 is the FY2025 closing balance, so every
    # FY2025 row here has an independent counterpart. If they disagree the layout is wrong
    # and nothing is written.
    # RECONCILE AGAINST A DIFFERENT DOCUMENT, because this page prints no total of its
    # own for the fund list. The ledger's FY2026 opening balance is the FY2025 closing
    # balance, so every FY2025 row here has an independent counterpart.
    #
    # THE BAR IS THE STABILIZATION ACCOUNTS, not every account. A column read off the
    # wrong x would break all of them at once, which is what this is for. But two
    # accounts disagree while the rest tie to the cent -- 8143, a scholarship, and 9001,
    # an agency account whose sign convention differs -- and that is two town documents
    # saying different things about the same account on the same date, which is a finding
    # rather than a bug in this reader. It is recorded per row, the way
    # `name_disagrees` records the other conflict this archive carries, instead of
    # stopping the extract.
    led = ledger()
    bad, noted = [], 0
    for r in body:
        r['ledger_balance'] = ''
        r['ledger_agrees'] = ''
        if r['fy'] != 2025:
            continue
        want = led.get(r['account'])
        if want is None:
            continue
        r['ledger_balance'] = round(want, 2)
        agrees = abs(want - r['balance']) <= 0.005
        r['ledger_agrees'] = 'yes' if agrees else 'no'
        if not agrees:
            noted += 1
            if r['account'] in STAB:
                bad.append('%s: the report says %.2f, the ledger says %.2f'
                           % (r['account'], r['balance'], want))
    if bad:
        print('FY2025 stabilization accounts do not tie to the general ledger:\n  %s'
              % '\n  '.join(bad), file=sys.stderr)
        return 1

    body.sort(key=lambda r: (r['fy'], r['account']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    for r in body:
        wr.writerow({k: (round(v, 2) if k == 'balance' else v) for k, v in r.items()})
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_trust_balance_detail.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d rows across %d years, FY2025 ties to the ledger'
              % (len(body), len({r['fy'] for r in body})))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d rows' % (os.path.relpath(OUT, ROOT), len(body)))
    for fy, page, n in found:
        print('  FY%d  page %s  %d accounts' % (fy, page, n))
    if led:
        n = sum(1 for r in body if r['fy'] == 2025 and r['ledger_agrees'])
        agree = sum(1 for r in body if r['ledger_agrees'] == 'yes')
        print('  %d FY2025 balances checked against the general ledger, %d agree'
              % (n, agree))
        for r in body:
            if r['ledger_agrees'] == 'no':
                print('    DISAGREES  %s %-34s report %.2f vs ledger %.2f'
                      % (r['account'], r['name'][:34], r['balance'],
                         r['ledger_balance']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
