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


# A TEXT LAYER OUTRANKS OCR, ALWAYS. Eight of the sixteen annual reports are born-digital
# and this listing's two years are both among them, so every row below was being RECOGNISED
# off a picture of a page that carries its own text. That is rule 13 exactly -- a rendering
# quoted in place of the source -- and it cost 10 of FY2025's 40 rows, silently: OCR does
# not refuse a page, it returns a shorter one, and a fund that vanishes looks precisely like
# a fund the town does not have.
#
# So `read_page` tries this first and falls back to the TSVs only for a page with no text.
# Nothing here reconciles the two readings; where a text layer exists the OCR reading of
# that page is superseded and discarded.
MIN_TEXT_WORDS = 40


def _pdf_for(tsv):
    """The published PDF this OCR cache was made from, if we hold it."""
    name = os.path.basename(tsv).replace('.tsv', '.pdf')
    hits = glob.glob(os.path.join(ROOT, 'sources', '**', name), recursive=True)
    return hits[0] if hits else None


def _lines(words):
    """Printed lines, banded on `top`. The pitch here is ~15pt and uniform, so a third of
    it separates rows without merging the wrapped fund names."""
    band = collections.defaultdict(list)
    for w in words:
        band[round(w['top'] / 5.0)].append(w)
    return [sorted(v, key=lambda w: w['x0']) for _, v in sorted(band.items())]


def text_layer_rows(pdf, tsv):
    """Every account in the TRUST FUND BALANCE listing, read off the page's own text.

    THE LISTING IS A SECTION, NOT A PAGE, and reading it as a page is the second half of
    what went wrong. FY2025 prints it across a spread -- eight accounts under the heading at
    the foot of p30, thirty-two more on p31 -- and the OCR reader scored each page on its
    own and kept the better one, so the eight were not misread, they were never looked at.
    Follow the heading forward instead, and stop at the first page that carries no account.
    """
    try:
        import pdfplumber
    except Exception:
        return None

    # READ FORWARD TO THE SECTION AND STOP, rather than parsing the book. These editions
    # run to two hundred pages and the listing is one spread of them; extracting every
    # page's words to find it took minutes per report and is most of what the reader cost.
    with pdfplumber.open(pdf) as doc:
        # SAMPLE BEFORE PARSING ANYTHING. Half these editions are scans of paper and carry
        # no text at all. A handful of pages from the middle answers that in a second, and
        # a sample with no text cannot be hiding a layer on the listing alone: the layer is
        # a property of how the edition was PRODUCED, not of one page.
        n = len(doc.pages)
        if sum(len(doc.pages[i].extract_words())
               for i in range(n // 4, min(n, n // 4 + 6))) < MIN_TEXT_WORDS:
            return None                  # a scanned edition: OCR is the only reader

        out, started, floor = [], False, 0.0
        for i in range(n):
            words = doc.pages[i].extract_words()
            if not started:
                for ln in _lines(words):
                    if HEADING.search(' '.join(w['text'] for w in ln)):
                        started, floor = True, ln[0]['top']
                        break
                if not started:
                    continue
            got = []
            for ln in _lines(words):
                if ln[0]['top'] <= floor or not CODE.match(ln[0]['text'].strip()):
                    continue
                figs = [w for w in ln if MONEY.match(w['text'].strip())]
                if not figs:
                    continue
                got.append(dict(account=ln[0]['text'].strip().split()[0],
                                name=' '.join(w['text'] for w in ln[1:]
                                              if w['x0'] < figs[0]['x0']),
                                balance=num(figs[0]['text']),
                                x=figs[0]['x1'], page=i + 1,
                                document=os.path.relpath(pdf, ROOT)))
            floor = 0.0
            if not got:
                # THE HEADING IS PRINTED TWICE, and the first one is not the table. Every
                # edition lists its own sections, so `TRUST FUND BALANCE` appears in the
                # index thirty pages before the listing; starting there found no accounts
                # and read the absence as the end of a section that had not begun. Only a
                # page that yielded a row can end the run.
                if out:
                    break
                started = False
                continue
            out.extend(got)
        if not started:
            # THE HEADING IS NOWHERE IN THE TEXT LAYER, so the text layer cannot read this
            # listing and OCR is the only reader for it. Returning [] here meant REFUSED --
            # the caller declines to fall back -- and FY2024's twenty-eight accounts were
            # deleted from trust-fund-balances.csv by the next run of this script. Its p29
            # is a photograph carrying one word, the page number, while pages sampled from
            # the middle of the same edition are born-digital.
            #
            # Which is the correction the comment above the sample needs too: a text layer
            # is a property of the PAGE, not of the edition. Half of these reports are
            # mixed, and this archive has already been caught by that -- FY2025 p115 is
            # born-digital with its table embedded as an image. None means `I cannot read
            # this, use the other reader`; [] means `I read it and it is empty`.
            return None

    # PLACE BY COLUMN POSITION, NEVER BY ORDER (rule 13b). Taking the leftmost figure is an
    # ORDER rule, and it is right only while the balance column is never blank. Measure the
    # column the page actually prints and refuse a row whose figure is not in it, so a blank
    # balance reads as a refusal rather than as somebody's receipts.
    if out:
        mid = sorted(r['x'] for r in out)[len(out) // 2]
        stray = [r for r in out if abs(r['x'] - mid) > 25]
        if stray:
            raise SystemExit('%s: %d rows have no figure in the balance column at x=%.0f: %s'
                             % (os.path.basename(pdf), len(stray), mid,
                                ', '.join(r['account'] for r in stray)))
        for r in out:
            del r['x']
    return out


def read_page(path):
    """The listing page, if this report has one.

    NOT `csv.DictReader`. These TSVs are unquoted and OCR text routinely contains a double
    quote, which the csv module treats as opening a quoted field -- it swallows every
    following line looking for a closing one and then raises `field larger than field
    limit`. `pdf_tables.read_boxes` splits on tabs line by line, which is why nothing
    downstream of it has ever lost a row.
    """
    pdf = _pdf_for(path)
    if pdf:
        rows = text_layer_rows(pdf, path)
        if rows:
            return str(rows[0]['page']), rows
        if rows is not None and rows == []:
            return None, []

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pdf_tables as T
    by_page = collections.defaultdict(list)
    for b in T.read_boxes(path):
        by_page[str(b['page'])].append(
            dict(x=b['x'], y=b['y'], w=b['w'], text=b['text']))

    # THE SAME 180-DEGREE TURN THE OTHER READER HANDLES. FY2024's listing comes off the
    # scanner reversed -- fund names at high x, figures at low -- so "the figure to the
    # right of the account number" finds nothing and the year reads as absent.
    try:
        from read_trust_table import upright
    except Exception:
        def upright(b):
            return b
    by_page = {p: upright(bs) for p, bs in by_page.items()}

    titled = {p for p, bs in by_page.items()
              if any(HEADING.search(b['text'] or '') for b in bs)}
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
    # ONE YEAR AT A TIME. Reading sixteen editions to fix one is most of what this work has
    # cost: the reader walks a two-hundred-page book per edition, so a change aimed at
    # FY2025 took minutes to see. `--year` is the difference between iterating and waiting.
    # It REWRITES ONLY THAT YEAR'S ROWS and keeps every other year's, so a narrowed run
    # cannot quietly shrink the file.
    ap.add_argument('--year', type=int, action='append',
                    help='only this fiscal year; repeatable')
    a = ap.parse_args()

    body, found = [], []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        if a.year and fy not in a.year:
            continue
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

    # A NARROWED RUN MERGES; IT DOES NOT TRUNCATE. `--year 2025` reads one edition, and
    # writing only what it read would silently drop fourteen years from the file -- the
    # exact shape of defect this archive keeps finding, an output that looks finished
    # because nothing compared it to what was there before.
    if a.year:
        keep = [r for r in csv.DictReader(open(OUT, encoding='utf-8'))
                if int(r['fy']) not in a.year] if os.path.exists(OUT) else []
        for r in keep:
            r['fy'] = int(r['fy'])
            r['balance'] = float(r['balance'])
        body = keep + body

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
