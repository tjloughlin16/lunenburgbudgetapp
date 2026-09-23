#!/usr/bin/env python3
"""Publish the COMBINED BALANCE SHEET pages, and register the ones that are refused.

    python3 scripts/extract_balance_sheet.py                # publish
    python3 scripts/extract_balance_sheet.py --check        # ...and fail if it is stale
    python3 scripts/extract_balance_sheet.py --page 4131-fy-2023-annual-town-report 24
                                                            # dump one page for a human

WHAT THIS IS, AND WHAT IT IS NOT

It is NOT a fresh reading of these pages. Thirteen of them were already read -- FY2011 to
FY2022, by a rendered-page transcription gated by `append_balance_sheet_year.py`, every
column footed to the total the town itself prints and tied to a SECOND document (the
special revenue schedule) read from different pages by a different instrument. That is a
stronger instrument than anything OCR can do here: `pdf_tables.py` names this page as one
where layout extraction recovers ZERO of its money tokens, and FY2023's OCR prints
`TOTAL LIABILITIES/FLIND EQUITY`. Re-deriving those rows would replace a reading proved
four ways with a worse one.

So this script does three things that were missing, and nothing else:

  1. IT RE-PROVES THE IDENTITY THE TABLE STATES ABOUT ITSELF, per fund-type column --
     total assets == total liabilities + total fund equity -- from the published rows and
     the published printed totals, and REFUSES TO PUBLISH a column that does not close.
     The gate has power to fail: change one cent of `balance-sheet-printed-totals.csv` and
     the column is dropped from the output and named in the refusals file.

  2. IT NAMES THE PAGE IN THE WORDS THE INGESTION QUEUE READS. `annual-report-pages.csv`
     credits a page as read only when a dataset carries `report_fy` and `page`. This
     dataset carried `fy` and `page_pdf`, so seventeen pages that are read, refused or
     published elsewhere all sat in the queue as `unread`. `report_fy` and `page` are
     added as columns here; they are aliases, derived, and the originals are untouched.

  3. IT REGISTERS THE REFUSALS, in `balance-sheet-refused.csv` and NOT in the data file.
     A row saying "refused" inside the data marks its own page READ and clears it off the
     queue, which is the opposite of what a refusal means.

THE MEMORANDUM CROSS-CHECK IS NOT AVAILABLE ON THIS TABLE, and that is a fact about the
page rather than a thing we skipped. The town-wide sheet prints SIX fund-type columns and
no `Totals (Memorandum Only)`. Read off the FY2022 page, printed page 24, the
`TOTAL LIABILITIES/FUND EQUITY` row is six observations and the rightmost is the long-term
debt account group:

    y=0.0580 x=0.3628  '$11.029,741.64 $5,005,585.64 $7,908,706.06'   (three, merged)
    y=0.0580 x=0.6409  '$2.092,432.29'
    y=0.0580 x=0.7518  '$6,409,987.50'
    y=0.0581 x=0.8590  '$38,749,085'

There is no seventh. The memorandum column exists on the FY2024/FY2025 ENTERPRISE sheet,
which is a different table in a dataset of its own, and its own `Proof` row is checked by
`verify_enterprise_balance_sheet.py`.

WHO ELSE WRITES `balance-sheet.csv`

`append_balance_sheet_year.py` does, when a new edition passes its gate, and it requires a
staged file whose header matches the real one EXACTLY. So a staged edition must now carry
`report_fy` and `page` as well, and this script must be re-run after an append. That is a
loud failure, not a silent one -- the appender prints both column lists and exits.
"""

import argparse
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

DATA = os.path.join(ROOT, 'sources', 'data')
READ = os.path.join(DATA, 'balance-sheet.csv')
TOTALS = os.path.join(DATA, 'balance-sheet-printed-totals.csv')
REFUSED = os.path.join(DATA, 'balance-sheet-refused.csv')
QUEUE = os.path.join(DATA, 'annual-report-pages.csv')
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')

ALIASES = ('report_fy', 'page')          # what the ingestion queue reads
# The pinned printed defects live in the verifier, with the amount and what is NOT
# established beside it. Imported rather than restated: a constant typed twice is rule 2's
# whole subject, and this one is load-bearing.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    'verify_balance_sheet', os.path.join(ROOT, 'scripts', 'verify_balance_sheet.py'))
_vbs = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_vbs)
DEFECTS = _vbs.PRINTED_DEFECTS

SECTION_TOTAL = {'assets': 'TOTAL ASSETS',
                 'liabilities': 'TOTAL LIABILITIES',
                 'fund_balances': 'TOTAL FUND EQUITY'}
# These files are CRLF and stay CRLF: a generated file with several authors gets
# clobbered, not merged, and a line-ending flip rewrites every row of the diff.
NEWLINE = '\r\n'
CENT = 0.005
DOLLAR = 1.0        # GENERAL LONG-TERM DEBT prints its totals to the dollar. Named, confined.


# ---------------------------------------------------------------------------
# PAGES THIS DATASET DOES NOT HOLD, AND WHY. One row each; never in the data file.
#
# Each reason is a statement about a page somebody opened, not about a matcher that
# found nothing -- rule 13c. The evidence for each is quoted in the report that
# accompanied this script and in PROVENANCE-balance-sheet.md.
# ---------------------------------------------------------------------------
REFUSALS = [
    dict(
        report_fy='2023', page='24',
        document='sources/town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf',
        table='COMBINED BALANCE SHEET - ALL FUND TYPES AND ACCOUNT GROUPS',
        state='refused', reason='cross-document check fails',
        detail=(
            'Transcribed, and it passes three of the four checks: every one of the six '
            'columns foots to its own printed TOTAL ASSETS, TOTAL LIABILITIES and TOTAL '
            'FUND EQUITY to the cent, the identity holds in all six, and the long-term '
            'debt mirror agrees. It fails the fourth. SPECIAL REVENUE fund equity '
            '$6,131,303.68 plus ENTERPRISE fund equity $3,812,502.24 is $9,943,805.92; '
            'the FY2023 special revenue schedule in the same report prints a GRAND TOTAL '
            'carried forward of $10,031,099.78. They differ by $87,293.86, where FY2011, '
            'FY2013, FY2019 and FY2022 agree to the cent. Refused by '
            'append_balance_sheet_year.py and not written down.'),
        quote=('OCR box, page 24, y=0.1047 x=0.3665 "54123.029.491 56.131,303.68" and '
               'y=0.1047 x=0.5884 "23.812,502 24 3,162,108.18" -- the TOTAL FUND EQUITY '
               'row, corroborating the rendered-page reading digit for digit'),
        closes=('the Town Accountant\'s FY2023 trial balance, which would say which of '
                'the two published tables is right'),
    ),
    dict(
        report_fy='2024', page='21',
        document='sources/town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf',
        table='Combining Balance Sheet - Enterprise Funds',
        state='published elsewhere', reason='not this table',
        detail=(
            'The page is not the town-wide combined balance sheet. It is the enterprise-'
            'funds combining sheet: four named ratepayer funds and a memorandum total, '
            'not six fund types. It IS read and published, in '
            'sources/data/enterprise-balance-sheet.csv, printing 1. FY2024 prints the '
            'same sheet again on page 28 and the two transcriptions agree exactly. The '
            'FY2024 table of contents nevertheless sends a reader to page 21 for '
            '"Balance Sheet for FY Ending June 30, 2024"; no town-wide sheet is in the '
            'book.'),
        quote=('OCR box, page 21, y=0.3547 x=0.0921 "PROOF" with ten 0.00 observations '
               'across the row, and y=0.3720 x=0.0977 "Total Liabilities and Fund '
               'Equity" against y=0.3735 x=0.8759 "6,886,028.60" -- a Proof row and a '
               'memorandum column, neither of which the town-wide sheet has'),
        closes=('the Town Accountant\'s FY2024 year-end submission to the Division of '
                'Local Services, which would say whether a town-wide sheet was produced '
                'and dropped in layout or never produced'),
    ),
    dict(
        report_fy='2024', page='28',
        document='sources/town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf',
        table='Combining Balance Sheet - Enterprise Funds',
        state='published elsewhere', reason='not this table',
        detail=(
            'The second printing of the same enterprise sheet as page 21. Read and '
            'published in sources/data/enterprise-balance-sheet.csv as printing 2; every '
            'one of its 38 figures and 25 printed totals agrees with page 21. Nothing '
            'may be summed across the two printings.'),
        quote=('OCR box, page 28, y ordered first line "Cash and cash equivale ASSETS" -- '
               'the same line list as page 21, and no real-estate-tax receivable rows at '
               'all, which every town-wide sheet in this archive carries'),
        closes=('the same FY2024 year-end submission to the Division of Local Services'),
    ),
    dict(
        report_fy='2025', page='25',
        document='sources/town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf',
        table='Combining Balance Sheet - Enterprise Funds',
        state='published elsewhere', reason='not this table',
        detail=(
            'Again the enterprise-funds sheet, not the town-wide one, and again read and '
            'published in sources/data/enterprise-balance-sheet.csv. The page prints 21 '
            'at its foot; 25 is its index in the PDF. The FY2025 contents lists no '
            'enterprise entry at all and one balance-sheet entry naming a town-wide '
            'sheet that is not in the book.'),
        quote=('OCR box, page 25, y ordered "Fixed Assets, net of accumulated '
               'depreciation" and "Amounts to be provided - payment of bonds" -- '
               'enterprise-fund lines; the town-wide sheet prints "FY23 REAL ESTATE '
               'TAXES" and "TAX LIENS FORECLOSURES" instead'),
        closes=('the Town Accountant\'s FY2025 year-end submission to the Division of '
                'Local Services'),
    ),
]

# `state` IS LOad-BEARING AND MUST NOT BE REMOVED. `map_annual_report_pages.py` marks a
# queued page read when any CSV in sources/data holds a row citing `report_fy` and `page`,
# and it skips a file carrying `state`, `rows_published` or `figures_reversed` -- the flag
# that says "this is a catalogue of what has been read, not a reading". Without it this
# file would clear all four refused pages off the queue while holding none of their
# figures, which is the silent zero rule 13c is about. `capital-plans-refused.csv` carries
# it for exactly this reason.
REFUSED_FIELDS = ['report_fy', 'page', 'state', 'document', 'table', 'reason', 'detail',
                  'quote', 'closes']


# ---------------------------------------------------------------------------

def read_csv(path):
    with open(path, newline='', encoding='utf-8') as fh:
        r = csv.DictReader(fh)
        return list(r.fieldnames), list(r)


def num(s):
    return float(str(s).replace(',', '').replace('$', '').strip() or 0)


def tolerance(fund):
    return DOLLAR if fund == 'long_term_debt' else CENT


def prove(rows, totals):
    """Which (edition, fund) columns close on the identity the table states about itself.

    Returns {(edition, fund): (ok, message)}. A column closes when the town's own printed
    TOTAL LIABILITIES plus its printed TOTAL FUND EQUITY equal its printed TOTAL ASSETS,
    AND our detail rows foot to each of those three printed totals.

    Both halves matter. The identity alone is a statement about the town's three printed
    numbers and says nothing about our reading; the footing alone says our reading sums to
    something without saying the sheet balances. Neither is a proof on its own.
    """
    printed = {}
    for t in totals:
        printed[(t['edition'], t['fund'], t['total_row'])] = num(t['amount'])

    footed = {}
    for r in rows:
        key = (r['edition'], r['fund'], SECTION_TOTAL[r['section']])
        footed[key] = footed.get(key, 0.0) + num(r['amount'])

    out = {}
    for (ed, fund, row), amount in sorted(printed.items()):
        out.setdefault((ed, fund), [True, [], []])
    for (ed, fund), state in out.items():
        tol = tolerance(fund)
        # 1. footing, per section
        for section, row in SECTION_TOTAL.items():
            p = printed.get((ed, fund, row))
            if p is None:
                state[0] = False
                state[1].append(f'no printed {row}')
                continue
            f = footed.get((ed, fund, row), 0.0)
            if abs(f - p) > tol:
                state[0] = False
                state[1].append(f'{row}: read {f:,.2f} vs printed {p:,.2f}')
        # 2. the identity
        a = printed.get((ed, fund, 'TOTAL ASSETS'))
        l = printed.get((ed, fund, 'TOTAL LIABILITIES'))
        e = printed.get((ed, fund, 'TOTAL FUND EQUITY'))
        if None in (a, l, e):
            state[0] = False
            state[1].append('a printed total is missing; the identity cannot be stated')
        elif abs((l + e) - a) > tol:
            # THE PAGE DISAGREES WITH ITSELF. That is a fact about the town's printed
            # report, not a misreading -- and the footing above has already proved the
            # reading, independently, against three totals the town printed. So the
            # identity has no power to detect a transcription error in this column; it is
            # reporting the sheet. Where the amount is PINNED TO THE PENNY in
            # `verify_balance_sheet.PRINTED_DEFECTS` the rows stay, and if the
            # discrepancy moves by a cent the pin stops matching and the column is
            # dropped. An unpinned failure drops the column.
            pinned = DEFECTS.get((ed, fund, 'identity'))
            gap = (l + e) - a
            if pinned and abs(abs(gap) - pinned[0]) <= tol:
                state[2].append(f'identity off by {gap:+,.2f} -- the PRINTED page '
                                f'disagrees with itself, pinned exactly')
            else:
                state[0] = False
                state[1].append(f'identity: liabilities {l:,.2f} + equity {e:,.2f} '
                                f'= {l + e:,.2f} vs assets {a:,.2f}')
        # 3. the sheet reprints TOTAL ASSETS at its foot; the town's two totals must agree
        re_ = printed.get((ed, fund, 'TOTAL LIABILITIES/FUND EQUITY'))
        if re_ is not None and a is not None and abs(re_ - a) > tol:
            pinned = DEFECTS.get((ed, fund, 'identity'))
            if pinned and abs(abs(re_ - a) - pinned[0]) <= tol:
                pass                      # the same printed defect, seen from its foot
            else:
                state[0] = False
                state[1].append(f'the page reprints {re_:,.2f} where TOTAL ASSETS is '
                                f'{a:,.2f}')
    return out


def build():
    """Returns (data_text, refused_text, proof, failures) -- the two files, as text.

    IT NEVER DROPS A ROW. This script's INPUT is its own output, so a gate that shrank the
    file would delete a correctly-read figure permanently on its second run -- which it
    did, once, on the three FY2019 FIDUCIARY TRUST and AGENCY rows, and the run after that
    read 0.00 where the town printed $3,841,163.85. So a column that does not close
    refuses the WHOLE WRITE and returns the failure. Nothing is written at all, and the
    message says to read the page again. That is `append_balance_sheet_year.py`'s rule --
    a year that does not tie is not written down -- applied to a file that already holds
    twelve years that do.
    """
    fields, rows = read_csv(READ)
    _, totals = read_csv(TOTALS)

    proof = prove(rows, totals)
    failures = {k: v[1] for k, v in proof.items() if not v[0]}

    out_fields = list(fields)
    for a in ALIASES:
        if a not in out_fields:
            out_fields.append(a)
    for r in rows:
        r['report_fy'] = r['fy']
        r['page'] = r['page_pdf']

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=out_fields, lineterminator=NEWLINE)
    w.writeheader()
    w.writerows(rows)
    data_text = buf.getvalue()

    refusals = sorted((dict(r) for r in REFUSALS),
                      key=lambda r: (r['report_fy'], int(r['page'])))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=REFUSED_FIELDS, lineterminator=NEWLINE,
                       extrasaction='ignore')
    w.writeheader()
    w.writerows(refusals)
    return data_text, buf.getvalue(), proof, failures


# ---------------------------------------------------------------------------
# --page: open the page and dump EVERY box on it. Rule 13c.
# ---------------------------------------------------------------------------

def dump_page(doc, page):
    import pdf_tables
    import read_trust_table

    path = os.path.join(OCR, doc if doc.endswith('.tsv') else doc + '.tsv')
    if not os.path.exists(path):
        sys.exit(f'no OCR at {path}\n'
                 f'available: ' + ', '.join(sorted(os.listdir(OCR))[:5]) + ' ...')

    # read_boxes splits on tabs and never invokes csv, so a `"` inside a recognised word
    # cannot swallow the rest of the file -- the failure the QUOTE_NONE rule exists for.
    boxes = [b for b in pdf_tables.read_boxes(path) if b['page'] == page]
    if not boxes:
        sys.exit(f'{doc} page {page}: the TSV holds no boxes for this page. That is a '
                 f'statement about this instrument, not about what the town printed. '
                 f'Open the PDF.')

    flipped = pdf_tables.looks_flipped(boxes)
    if flipped:
        boxes = pdf_tables.unflip(boxes)
    boxes = read_trust_table.split_merged(boxes)
    slope = read_trust_table.skew(boxes)
    band = pdf_tables.row_band(boxes)

    print(f'{doc} page {page}')
    print(f'  {len(boxes)} boxes after splitting merged observations')
    print(f'  half-turn out: {flipped}' + ('  (unflipped below)' if flipped else ''))
    print(f'  measured rotation: {slope:+.5f}   row band (half the page pitch): {band:.5f}')
    print(f'  Y = y - slope*x is the coordinate a row shares.')
    print(f'  y is measured from the FOOT of the page, so this reads top-to-bottom by')
    print(f'  DESCENDING Y. Sorting the other way prints a balance sheet upside down --')
    print(f'  fund equity first -- which looks like a flipped scan and is not one.')
    print()
    print(f'{"Y":>8} {"y":>8} {"x":>8} {"conf":>5}  text')
    for b in sorted(boxes, key=lambda b: (-(b['y'] - slope * b['x']), b['x'])):
        Y = b['y'] - slope * b['x']
        print(f'{Y:8.4f} {b["y"]:8.4f} {b["x"]:8.4f} {b["conf"]:5.2f}  {b["text"]}')

    # The text layer, if there is one. Some of these pages read far better from it.
    try:
        import pdfplumber
    except ImportError:
        return
    pdf = None
    for d in ('sources/town-annual-reports/docs',):
        cand = os.path.join(ROOT, d, os.path.basename(path).replace('.tsv', '.pdf'))
        if os.path.exists(cand):
            pdf = cand
            break
    if not pdf:
        return
    with pdfplumber.open(pdf) as f:
        if page > len(f.pages):
            return
        text = f.pages[page - 1].extract_text() or ''
    print()
    print(f'--- PDF TEXT LAYER, {os.path.basename(pdf)} page {page} '
          f'({len(text)} chars) ---')
    print(text if text.strip() else '(empty: this page is a scan)')


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true',
                    help='fail if either output file is stale')
    ap.add_argument('--page', nargs=2, metavar=('DOC', 'PAGE'),
                    help='dump every box on one page, for a human')
    a = ap.parse_args()

    if a.page:
        return dump_page(a.page[0], int(a.page[1]))

    data_text, refused_text, proof, failures = build()
    closed = sum(1 for v in proof.values() if v[0])

    if failures:
        for (ed, fund), why in sorted(failures.items()):
            print(f'REFUSED  {ed} {fund}: {"; ".join(why)}')
        print()
        print('Nothing was written. Read the page again; do not adjust a printed total to')
        print("make it tie. If the town's own page disagrees with itself, that is a")
        print('finding and it belongs in PRINTED_DEFECTS in verify_balance_sheet.py,')
        print('pinned to the exact amount, with what it does NOT establish beside it.')
        sys.exit(1)

    if a.check:
        bad = []
        for path, want in ((READ, data_text), (REFUSED, refused_text)):
            have = (open(path, encoding='utf-8', newline='').read()
                    if os.path.exists(path) else None)
            if have != want:
                bad.append(os.path.relpath(path, ROOT))
        if bad:
            print('STALE: ' + ', '.join(bad))
            print('Run: python3 scripts/extract_balance_sheet.py')
            sys.exit(1)
        pinned = sum(len(v[2]) for v in proof.values())
        print(f'balance sheet: {closed} of {len(proof)} fund-type columns close on the '
              f'identity ({pinned} pinned printed defect(s)); both files reproduce.')
        return

    with open(READ, 'w', encoding='utf-8', newline='') as fh:
        fh.write(data_text)
    with open(REFUSED, 'w', encoding='utf-8', newline='') as fh:
        fh.write(refused_text)
    print(f'{os.path.relpath(READ, ROOT)}: '
          f'{data_text.count(NEWLINE) - 1} figure rows')
    print(f'{os.path.relpath(REFUSED, ROOT)}: '
          f'{refused_text.count(NEWLINE) - 1} refused page(s)')
    print(f'{closed} of {len(proof)} fund-type columns close on '
          f'assets = liabilities + fund equity, each footed to a total the town printed.')
    for k, v in sorted(proof.items()):
        if not v[0]:
            print(f'  DROPPED {k[0]} {k[1]}: {"; ".join(v[1])}')
        for note in v[2]:
            print(f'  PRINTED DEFECT, published anyway: {k[0]} {k[1]}: {note}')


if __name__ == '__main__':
    main()
