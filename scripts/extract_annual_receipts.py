#!/usr/bin/env python3
"""Receipts by source, every year the annual town report prints them.

The archive holds the town's revenue by line for **FY2026 only**. The annual town reports
carry the same table back to FY2011, which is the difference between knowing what the town
received last year and knowing whether last year was normal.

**Every year is written. Not every year is checked, and the difference is recorded on
every row.** The report prints its own GRAND TOTAL and its own summary by category, so
there are two independent checks:

    sum of the detail lines       == GRAND TOTAL
    sum of the summary categories == GRAND TOTAL

A year where both pass is `reconciled`. A year where they cannot be run -- FY2011's page is
clipped in the town's own scan, so the third column's amounts and the GRAND TOTAL are past
the paper edge -- is `partial`, and carries the reason. The rows are still worth having;
what must not happen is a partial year being summed as though it were a complete one, so
the `status` column travels with every row and
`sources/data/PROVENANCE-annual-report-receipts.md` states per year what is missing.

**A partial year's total is not the town's revenue for that year.** It is the part of the
table that survived. Nothing downstream may add these up across years without splitting on
`status` first.

That is not belt and braces. Separating the summary block from the detail is the hard part
of reading this page -- the town prints both on the same physical lines, three columns
across, and plain-mode extraction interleaves them into one string. An early version
classified five categories as detail and the two sums came out wrong by exactly equal and
opposite amounts, $3,333,429.48 each way. The classifier is a heuristic; the arithmetic is
not, and a year that does not reconcile is reported and skipped rather than guessed at.

Rule 13: when an extract has a total the source itself prints, reconcile to it.

    python3 scripts/extract_annual_receipts.py
    python3 scripts/extract_annual_receipts.py --boxes <dir>   # include the scanned years
"""

import argparse
import csv
import glob
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pdf_tables as T
import report_pages as RP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-budget', 'docs')
OUT = os.path.join(ROOT, 'sources', 'data', 'annual-report-receipts.csv')
PROV = os.path.join(ROOT, 'sources', 'data',
                    'PROVENANCE-annual-report-receipts.md')

PAIR = re.compile(r"([A-Z][A-Za-z0-9&/\.\,\'\-\# ]{2,60}?)\s*\$\s?([\d,]+\.\d\d)")


def loose(phrase):
    """A pattern for `phrase` that survives the source breaking words apart.

    FY2018 page 28 prints `SUMMARY OF RECEIPT S`. An exact match on
    `SUMMARY OF RECEIPTS` therefore found nothing, the summary window was never located,
    and every category subtotal was counted as detail -- $120,579,065.28 against a printed
    $40,193,021.76, three times over.

    The same defect had already been found and fixed in `extract_placement_counts.py`,
    where four of twelve years read `studen ts`, `ou tside` and `out-  side`. Writing the
    fix twice is the cost of not noticing it was the same fix.
    """
    return r'[-\s]*'.join(re.escape(c) for c in phrase if not c.isspace())


SUMMARY_HEADING = re.compile(loose('SUMMARY OF RECEIPTS'), re.I)

# The categories the town's own SUMMARY OF RECEIPTS block prints. A closed set, because it
# is the town's set and not ours -- and if a year adds one, the reconciliation below fails
# and that year is skipped rather than silently mis-split. That is the intended behaviour:
# a new category is a change in the source and should be looked at by somebody.
SUMMARY_CATEGORIES = [
    'TAXES & EXCISES', 'FEES', 'LICENSES AND PERMITS', 'LICENSES/PERMITS',
    'STATE REVENUE', 'SPECIAL ASSESSMENTS', 'FINES & FORFEITS', 'INVESTMENT INCOME',
    'EARNINGS ON INVESTMENTS', 'TRANSFER FROM OTHER FUNDS', 'TRANSFERS FROM OTHER FUNDS',
    'NON RECURRING REVENUE', 'DEPARTMENTAL REVENUE', 'MISCELLANEOUS REVENUE',
]


def norm(label):
    return re.sub(r'\s+', ' ', (label or '').strip().upper().rstrip(':'))


def squash(label):
    """A label with every space, hyphen and punctuation mark removed, for COMPARISON only.

    Never for display, and never stored -- what the page printed is what gets written to
    the CSV. This exists solely so that comparing a label to a known name survives the
    ways the text layer breaks words apart.

    It has to, because the breakage is not exotic. FY2018 page 28 renders its labels as:

        GRAND T OT AL              -> GRANDTOTAL
        T AXES & EXCISES           -> TAXES&EXCISES
        REAL EST AT E T AXES       -> REALESTATETAXES

    Matching those exactly failed, so the GRAND TOTAL and every category subtotal were
    filed as detail rows and the year summed to $119,723,580.93 against a printed
    $40,193,021.76 -- three times over, from a page whose figures were all read correctly.

    This is the third form the same defect has taken today: `SUMMARY OF RECEIPT S` in a
    heading, `studen ts` and `ou tside` in prose, and now single letters split out of
    words in a table. The lesson is not about any one of them. **A pattern matched against
    extracted text is matched against our rendering of the document, so every comparison
    has to tolerate the ways that rendering breaks** -- which is rule 13 with a regex in it.
    """
    return re.sub(r'[^A-Z0-9&]', '', (label or '').upper())


def fiscal_year(name):
    m = re.search(r'fy-?(\d{4})', name)
    return int(m.group(1)) if m else None


CATALOGUE = os.path.join(ROOT, 'sources', 'data', 'annual-report-catalogue.csv')


def catalogue_receipts_pages(edition):
    """Where this year's receipts table is, according to the catalogue.

    **Not by searching for a heading.** The previous version looked for
    `SUMMARY OF RECEIPTS` and reported FY2023 as having no receipts table at all. It has
    one, on page 25; `SUMMARY OF RECEIPTS` is the name of a *box inside* the page, and that
    year's OCR did not render it.

    Reading all sixteen reports end to end showed what the pages are actually titled, and
    it is nearly uniform where the box is not: `FY 2014 RECEIPTS - JUNE 2014`,
    `FY 2015 RECEIPTS - JUNE 2015`, and so on through FY2023. Thirteen consecutive years
    under a title nobody had searched for, because the search had been built from the one
    year somebody happened to look at.

    Two years genuinely have no such table, and that is a finding rather than a gap:
    FY2024's accountant section was replaced wholesale with MUNIS schedules, and FY2025
    publishes no general fund revenue table at all.
    """
    pages = set()
    if not os.path.exists(CATALOGUE):
        return []
    for r in csv.DictReader(open(CATALOGUE)):
        if r['edition'] != edition:
            continue
        blob = f"{r['name']} {r['printed_heading']}"
        if not re.search(r'RECEIPTS', blob, re.I):
            continue
        # Several other tables mention receipts without being the receipts table, and
        # taking them produced years with six "receipts pages" summing to a fifth of the
        # real figure each. `GENERAL FUND REVENUES FY nn` is a one-page summary beside the
        # detail; the special revenue fund schedules carry a `Receipts` COLUMN and are a
        # different dataset with a different grain.
        if re.search(r'GENERAL FUND REVENUES|New Growth|Assessment|SPECIAL REVENUE|'
                     r'TRUST|CAPITAL PROJECT|ENTERPRISE|BALANCE SHEET', blob, re.I):
            continue
        for a, b in re.findall(r'(\d+)\s*[-\u2013]\s*(\d+)', r['pages'] or ''):
            if int(b) >= int(a) and int(b) - int(a) < 20:
                pages.update(range(int(a), int(b) + 1))
        for n in re.findall(r'(?<![\d-])(\d{1,3})(?![\d-])', r['pages'] or ''):
            pages.add(int(n))
    return sorted(pages)


def receipts_pages(lines_by_page, edition=None):
    """The receipts page(s) for one report.

    The catalogue is authoritative. Content matching is kept only as a fallback for a
    document the catalogue does not cover, and it is deliberately loose about the heading
    while strict about the shape -- a page of the receipts table carries far more
    label/amount pairs than anything else in the book.
    """
    if edition:
        listed = [p for p in catalogue_receipts_pages(edition) if p in lines_by_page]
        if listed:
            return listed
    out = []
    for page, lines in lines_by_page.items():
        text = '\n'.join(lines).upper()
        if re.search(r'RECEIPTS\s*[-\u2013]\s*JUNE|SUMMARY OF RECEIPTS', text) \
                and len(T.MONEY_TOKEN.findall(text)) > 40:
            out.append(page)
    return sorted(out)


def split_summary(lines):
    """Detail rows, summary categories, and the printed grand total, off ONE page.

    Two tests, and both are needed, because each one alone gets it wrong in a way the
    other catches:

    **The window.** The summary block runs from the `SUMMARY OF RECEIPTS` heading to the
    rule of `=` beneath it. Name alone is not enough, because the same label appears twice
    on the page -- once as a detail line and once as its own category, at the same value,
    for any category with a single member. In FY2022 that is
    `TRANSFERS FROM OTHER FUNDS $2,391,150.83` and `INVESTMENT INCOME $24,440.01`, and
    classifying both occurrences as summary moved exactly $2,415,590.84 from one side of
    the reconciliation to the other.

    **The category list.** The window alone is not enough either, because the block sits in
    the rightmost of three columns and plain-mode extraction interleaves all three onto one
    line. A detail row on a line inside the window -- `STATE OWNED LAND $32,522.00` in
    FY2022 -- is otherwise swept in with it.

    Position would settle it and is not available: plain mode is the only instrument that
    reads this page, and the coordinate walk reports every run at x=0, because each line is
    a single text-showing operation with the columns spaced by kerning.
    """
    cats = {squash(c) for c in SUMMARY_CATEGORIES}
    begin = [n for n, l in enumerate(lines) if SUMMARY_HEADING.search(l)]
    if not begin:
        # No summary box in the text. That does NOT mean no receipts: the box is a small
        # panel in the corner of the page and is often the first thing a scan loses, while
        # the detail -- a hundred label/amount pairs -- comes through intact. Returning
        # nothing here reported FY2018 through FY2023 as having no receipts table at all,
        # when what was missing was the panel that makes them checkable.
        #
        # So the detail is extracted and the year is marked partial, which is exactly what
        # partial means: real rows, no way to verify them.
        detail, summary = [], []
        for line in lines:
            for m in PAIR.finditer(line):
                label, value = m.group(1).strip(), float(m.group(2).replace(',', ''))
                key = squash(label)
                if key.startswith('GRANDTOTAL'):
                    continue
                # Without a window the category subtotals can only be told from the detail
                # by name. That over-excludes a label printed twice -- a category with one
                # member appears as both -- so the year cannot reconcile and is marked
                # partial, which is honest. What it must NOT do is count a subtotal as
                # detail and report three times the town's revenue.
                (summary if key in cats else detail).append((label, value))
        return detail, summary, None
    b = begin[0]
    rule = [n for n, l in enumerate(lines) if '====' in l and n > b]
    e = rule[0] if rule else len(lines)

    detail, summary, grand = [], [], None
    for n, line in enumerate(lines):
        for m in PAIR.finditer(line):
            label, value = m.group(1).strip(), float(m.group(2).replace(',', ''))
            key = squash(label)
            if key.startswith('GRANDTOTAL'):
                grand = value
            elif b <= n <= e + 2 and key in cats:
                summary.append((label, value))
            else:
                detail.append((label, value))
    return detail, summary, grand


def missing_figures(lines, detail, summary, grand):
    """Labels the page prints with no figure beside them.

    This is the evidence for calling a year partial rather than merely unreconciled. On
    FY2011's receipts page the town's own scan is clipped at the right edge: the summary
    categories and `GRAND TOTAL` are printed and their amounts are not on the paper. A
    label with no figure is the visible end of a table that was cut off.

    It is deliberately not a guess at how much is missing. We can say which lines have no
    figure; we cannot say what the figures were.
    """
    text = '\n'.join(lines).upper()
    priced = {norm(k) for k, _ in detail} | {norm(k) for k, _ in summary}
    missing = []
    for cat in SUMMARY_CATEGORIES:
        key = norm(cat)
        if key in text and key not in priced:
            missing.append(cat)
    if 'GRAND TOTAL' in text and grand is None:
        missing.append('GRAND TOTAL')
    return missing


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boxes', default=os.path.join(ROOT, 'sources', 'town-budget', 'ocr'),
                    help='directory of ocr_pdf.swift --boxes TSVs')
    args = ap.parse_args()

    rows, ledger = [], []
    pdfs = sorted(glob.glob(os.path.join(DOCS, '*annual-town-report*.pdf')),
                  key=lambda p: fiscal_year(os.path.basename(p)) or 0)

    for path in pdfs:
        name = os.path.basename(path)
        fy = fiscal_year(name)
        # The FY2016 addendum is not a supplement -- it is the missing half of that
        # year's financial record, and it holds the only complete copy of the FY2016
        # receipts table. The main report's version is clipped at the page edge.
        edition0 = f'FY{fy}' + ('-addendum' if 'addendum' in name else '')
        lines_by_page = RP.load(edition0)
        mode_of = 'page cache'
        edition = 'FY' + str(fy) + ('-addendum' if 'addendum' in name else '')
        pages = receipts_pages(lines_by_page, edition)

        # One page at a time. Pooling them reconciles one table's detail against another
        # table's total, which is how a $2.2M printed figure came to be compared with
        # $31.8M of extracted rows.
        wrote_any = False
        for page in pages:
            lines = [l for l in lines_by_page[page] if l.strip()]
            detail, summary, grand = split_summary(lines)
            if not detail:
                continue
            sd = round(sum(v for _, v in detail), 2)
            sc = round(sum(v for _, v in summary), 2)
            absent = missing_figures(lines, detail, summary, grand)

            if grand is None:
                status = 'check failed' if grand is not None else 'no check'
                why = ('the page prints no GRAND TOTAL figure, so neither check can be '
                       'run')
            elif abs(sd - grand) > 0.02 or abs(sc - grand) > 0.02:
                status = 'check failed' if grand is not None else 'no check'
                why = (f'does not tie: detail {sd:,.2f} ({sd - grand:+,.2f}), '
                       f'categories {sc:,.2f} ({sc - grand:+,.2f}), '
                       f'printed {grand:,.2f}')
            else:
                status = 'checked'
                why = ''

            if absent:
                why = ((why + '; ') if why else '') + \
                    f'printed with no figure beside it: {", ".join(absent)}'

            ledger.append({'fy': fy, 'document': name, 'page': page, 'mode': mode_of,
                           'status': status, 'sources': len(detail),
                           'extracted': sd, 'printed': grand, 'why': why,
                           'absent': absent})
            for label, value in detail:
                rows.append({'fy': fy, 'source': label, 'amount': f'{value:.2f}',
                             'status': status, 'document': name, 'page': page})
            wrote_any = True
        if not wrote_any:
            ledger.append({'fy': fy, 'document': name, 'page': '', 'mode': mode_of,
                           'status': 'not found', 'sources': 0, 'extracted': None,
                           'printed': None, 'absent': [],
                           'why': 'the catalogue lists no receipts table for this year, '
                                  'and reading the report end to end found none -- FY2024 '
                                  'replaced the accountant section with MUNIS schedules '
                                  'and FY2025 publishes no general fund revenue table'})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'source', 'amount', 'status',
                                           'document', 'page'])
        w.writeheader()
        w.writerows(rows)

    reconciled = [r for r in ledger if r['status'] == 'checked']
    partial = [r for r in ledger if r['status'] in ('check failed', 'no check')]
    notfound = [r for r in ledger if r['status'] == 'not found']

    print("checked -- both checks tie to the report's own GRAND TOTAL:")
    for r in reconciled:
        print(f"  FY{r['fy']}  {r['sources']:>4} sources  {r['printed']:>16,.2f}  p{r['page']}")
    if partial:
        print("\nnot checked by arithmetic -- the rows are the town's, "
              "what is missing is the check:")
        for r in partial:
            print(f"  FY{r['fy']}  {r['sources']:>4} sources  {r['extracted']:>16,.2f}  "
                  f"p{r['page']}\n        {r['why']}")
    if notfound:
        print('\nno receipts page found:')
        for r in notfound:
            print(f"  FY{r['fy']}: {r['why']}")

    # The denominator.
    print(f"\n{len(reconciled)} checked + {len(partial)} unchecked of "
          f"{len(pdfs) - 1} reports; {len(rows)} source-years "
          f"({sum(1 for r in rows if r['status'] == 'checked')} checked, "
          f"{sum(1 for r in rows if r['status'] != 'checked')} not)")
    print(f'wrote {os.path.relpath(OUT, ROOT)}')

    write_provenance(ledger, pdfs)
    print(f'wrote {os.path.relpath(PROV, ROOT)}')


def write_provenance(ledger, pdfs):
    """The provenance report, generated from the run rather than written beside it.

    Rule 12 wants the address, the publisher's filename and our copy with a sha256 for
    every source. Rule 2 wants every figure derived rather than typed -- which applies
    with particular force here, because this document's whole job is to say which figures
    were checked, and a hand-maintained list of that would be wrong within a week.

    It leads with the partial years. A reader who takes one number out of the CSV needs to
    know before anything else whether that year's table was complete.
    """
    hashes = {os.path.basename(p): sha256(p) for p in pdfs}
    partial = [r for r in ledger if r['status'] in ('check failed', 'no check')]
    reconciled = [r for r in ledger if r['status'] == 'checked']
    notfound = [r for r in ledger if r['status'] == 'not found']

    L = []
    L.append('# Receipts by source, and which years were checked')
    L.append('')
    L.append('**Generated by `scripts/extract_annual_receipts.py`. Do not edit.** Every')
    L.append('figure here is computed from the run that produced')
    L.append('`sources/data/annual-report-receipts.csv`, so it states what the extractor')
    L.append('actually did rather than what somebody wrote down when it did something else.')
    L.append('')
    L.append('The town prints its own `GRAND TOTAL` and its own summary by category, giving')
    L.append('two independent checks. A year passing both is **reconciled**. A year where')
    L.append('they cannot be run is **partial** -- the rows are real and the table they came')
    L.append('from was not whole.')
    L.append('')
    L.append('## Do not add a partial year to a reconciled one')
    L.append('')
    L.append("A partial year's total is not the town's revenue for that year. It is the part")
    L.append('of the table that survived. The `status` column is on every row of the CSV for')
    L.append('this reason, and anything that aggregates across years must split on it first.')
    L.append('')

    if partial:
        L.append('## Partial years')
        L.append('')
        for r in sorted(partial, key=lambda r: r['fy']):
            L.append(f"### FY{r['fy']} — {r['sources']} sources, "
                     f"${r['extracted']:,.2f} extracted")
            L.append('')
            L.append(f"- **Why it is partial:** {r['why']}")
            if r['printed'] is not None:
                L.append(f"- The report prints a GRAND TOTAL of **${r['printed']:,.2f}**; "
                         f"we extracted **${r['extracted']:,.2f}**, a difference of "
                         f"**${r['extracted'] - r['printed']:+,.2f}**.")
            else:
                L.append('- **The report prints no GRAND TOTAL figure on this page.** '
                         'There is nothing to reconcile against, so the extracted total '
                         'is unverified in both directions: we cannot show that nothing '
                         'was dropped, and we cannot show that nothing was double-counted.')
            if r['absent']:
                L.append(f"- Printed on the page with **no figure beside it**: "
                         f"{', '.join(r['absent'])}.")
            L.append(f"- Source: `{r['document']}`, page {r['page']}, read by "
                     f"{r['mode']}.")
            L.append(f"- sha256 `{hashes.get(r['document'], 'unknown')}`")
            L.append('')

    L.append('## Reconciled years')
    L.append('')
    L.append('| FY | sources | GRAND TOTAL printed | extracted | page | read by |')
    L.append('|---|---:|---:|---:|---|---|')
    for r in sorted(reconciled, key=lambda r: r['fy']):
        L.append(f"| {r['fy']} | {r['sources']} | ${r['printed']:,.2f} | "
                 f"${r['extracted']:,.2f} | {r['page']} | {r['mode']} |")
    L.append('')
    L.append('Both checks pass for every row above, so **nothing was dropped**: a source')
    L.append('absent in one of these years is a line the town did not print that year, not')
    L.append('a line the extractor lost.')
    L.append('')

    if notfound:
        L.append('## Years with no receipts page found')
        L.append('')
        L.append('Not years the town published nothing. Each of these needs looking at.')
        L.append('')
        for r in sorted(notfound, key=lambda r: r['fy']):
            L.append(f"- **FY{r['fy']}** — {r['why']}")
        L.append('')

    L.append('## Our copies')
    L.append('')
    L.append('| document | sha256 |')
    L.append('|---|---|')
    for name in sorted(hashes):
        L.append(f'| `{name}` | `{hashes[name]}` |')
    L.append('')

    with open(PROV, 'w') as fh:
        fh.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
