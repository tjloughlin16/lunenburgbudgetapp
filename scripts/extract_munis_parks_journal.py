"""The parks funds' MUNIS journal, FY2023-FY2026 -- every posting to funds 1500 and 1523.

    python3.11 scripts/extract_munis_parks_journal.py           # extract, tie, redact, write
    python3.11 scripts/extract_munis_parks_journal.py --check   # rebuild in memory; fail if an
                                                                #   output differs or a tie fails
    python3.11 scripts/extract_munis_parks_journal.py --review  # print every DISTINCT vendor and
                                                                #   description AFTER redaction

THE SOURCE. `glytdbud`, YEAR-TO-DATE BUDGET REPORT, `FOR 2026 13`, `Print journal detail: Y`
from `2023/ 0` to `2026/13`, generated 11/05/2026 13:37: 17 pages, funds 1500 (Park
Revolving) and 1523 (Park Gift). The Town's answer to item 2 of this project's records request
of 5 November 2026 (`sources/town-ledgers/expenses/PROVENANCE-fy2025-fy2026-p13-gf-all.md`).
The raw is held PRIVATE (`sources/data/redactions.csv`, row 08c9d29b) and is read from the
gitignored local copy, or fetched from the private bucket into it. What this script writes is
OUR redacted reading:

    sources/data/munis-parks-journal.csv            one row per journal line
    sources/data/munis-parks-journal-accounts.csv   one row per account: the FY2026 figures the
                                                    report prints

HOW THE PAGE IS READ: exactly as the school journal is -- the same monospaced MUNIS printout,
rebuilt character by character into fixed columns (`extract_munis_school_journal.page_lines`)
and cut by column (`split_journal`). Which journal source posts to which printed column is
`journal.COLUMN_OF`, the one table every journal report reads.

WHAT TIES -- and the script refuses to write if any one fails (rule 13):

  1. Every account's FY2026 figures, as printed: ORIGINAL APPROP = FY2026 `BUC`; TRANFRS/ADJSTMTS
     = FY2026 `BUA`; YTD ACTUAL = FY2026 actuals; ENC/REQ = FY2026 encumbrances.
  2. Every `TOTAL` line, against the accounts above it in its section.
  3. The p16 GRAND TOTAL, against every account.
  4. AGAINST OTHER DOCUMENTS, for fund 1500. FY2023's receipts and disbursements equal the FY2023
     annual town report's Park User Fees row (`special-revenue-read.csv`), and that row's closing
     balance carried forward by each year's journal receipts less spending reaches the FY2026
     special-revenue report's OPENING balance (`finance.json` measure `sr-1500`). So the journal
     is the fund's whole cash flow, and FY2024 and FY2025 closings follow from it.

OUR REDACTION (notes/process/DATA-PRIVACY.md, the one test). Vendors, instructors and staff are
shown, and so are organisations paying field fees and a donor to the gift fund. MASKED: a
private person paying a park PROGRAM fee -- a family paying for its own child's programme is
the `fees` case of the masked list. The receipts are DECLARED below, by receipt number, and the
script refuses if any other receipt description names a person in `SURNAME, FIRST` form, so a
new delivery cannot slip one through. The receipt number goes too: the Town's cash book would
resolve it to the payer.
"""
import csv
import hashlib
import io
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import extract_munis_school_journal as S  # noqa: E402
from journal import COLUMN_OF  # noqa: E402

RAW_KEY = 'town-ledgers/account-details/account-details-fy2023-fy2026-p13-funds-1500-1523-journal.pdf'
RAW_SHA256 = '08c9d29bc48e4661d0398520ed09b5d4f6e9131fa4db560343df2a837c0dc204'
RAW_LOCAL = os.path.join(ROOT, 'build', 'private', 'munis', 'parks', 'journal-1500-1523.pdf')
PAGES = 17
DATA = os.path.join(ROOT, 'sources', 'data')
OUT = os.path.join(DATA, 'munis-parks-journal.csv')
OUT_ACCOUNTS = os.path.join(DATA, 'munis-parks-journal-accounts.csv')

MASK = '[payer masked]'
# Receipt number -> why. Each is a private person paying a park programme fee.
MASKED_RECEIPTS = {
    '949452': 'a private person paying a park programme fee',
    '1024017': 'a private person paying a park programme fee',
}
PERSON_PAYER = re.compile(r'/\s*[A-Z][A-Z\'-]+,\s*[A-Z]')

FIELDS = ['fund', 'fund_name', 'section', 'account', 'object', 'object_name',
          'account_description', 'side', 'fiscal_year', 'period', 'journal', 'effective_date',
          'source', 'posts_to', 'amount', 'ref_type', 'vendor_no', 'vendor', 'doc_type',
          'doc_no', 'description', 'check_no', 'page', 'line', 'masked']
ACCOUNT_FIELDS = ['fund', 'section', 'account', 'object', 'account_description', 'side',
                  'original_approp', 'transfers_adjustments', 'revised_budget', 'ytd_actual',
                  'encumbrances', 'available_budget', 'pct_used', 'journal_lines', 'page']
FIG_TO_COL = {'original_approp': 'original_budget', 'transfers_adjustments': 'transfer',
              'ytd_actual': 'actual', 'encumbrances': 'encumbrance'}
# The page head: the run's title (`YTD 1500 1523`, printed letter-spaced) and the two
# column-heading lines, one of which repeats the section name on a continuation page.
HEADER = re.compile(r'^Y TD\s|ORIGINAL\s+TRANFRS|APPROP\s+ADJSTMTS')
SECTION = re.compile(r'^(\d{5,8}) ((?:EXPENSES|REVENUES) .*)$')


def load_raw():
    if not os.path.exists(RAW_LOCAL):
        import archive_storage as A
        blob = A.get_private('raw/' + RAW_KEY)
        os.makedirs(os.path.dirname(RAW_LOCAL), exist_ok=True)
        with open(RAW_LOCAL + '.part', 'wb') as fh:
            fh.write(blob)
        os.replace(RAW_LOCAL + '.part', RAW_LOCAL)
    blob = open(RAW_LOCAL, 'rb').read()
    sha = hashlib.sha256(blob).hexdigest()
    if sha != RAW_SHA256:
        raise SystemExit(f'{RAW_LOCAL}: sha256 {sha[:12]}, expected {RAW_SHA256[:12]}')
    return blob


def parse(blob):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(blob)
    if len(doc) != PAGES:
        raise SystemExit(f'{len(doc)} pages, expected {PAGES}')
    accounts, totals, problems = [], [], []
    section = obj = obj_name = ''
    sec_start = 0
    pending = cur = grand = None
    for pn in range(1, PAGES + 1):
        for ln, l in enumerate(S.page_lines(doc[pn - 1]), 1):
            if S.FURNITURE.match(l) or HEADER.search(l):
                continue
            if pn == PAGES or 'END OF REPORT' in l:
                continue                      # the report-options page
            if S.J.match(l):
                f = S.split_journal(l)
                f.update(page=str(pn), line=str(ln))
                cur['lines'].append(f)
                continue
            m = S.ACC.match(l)
            if m:
                pending = (m.group(0).split()[0], m.group(1), m.group(8), m.group(10).strip())
                continue
            m = S.FIG.match(l)
            if m and pending:
                acct, fund, digit, desc = pending
                cur = {'fund': fund, 'section': section, 'account': acct, 'object': obj,
                       'object_name': obj_name, 'account_description': desc,
                       'side': {'2': 'expense', '4': 'revenue'}.get(digit, digit),
                       'page': str(pn), 'lines': []}
                for k, v in zip(S.FIGURE_FIELDS, m.groups()[:6]):
                    cur[k] = S.dec(v)
                cur['pct_used'] = m.group(7)
                accounts.append(cur)
                pending = None
                continue
            m = S.TOT.match(l)
            if m:
                figs = [S.dec(x) for x in m.groups()[2:8]]
                if m.group(1) == 'GRAND TOTAL':
                    grand = figs
                else:
                    totals.append((pn, m.group(2).strip(), figs, len(accounts), sec_start))
                continue
            m = SECTION.match(l)
            if m:
                section, sec_start = m.group(2).strip(), len(accounts)
                continue
            m = S.ORG.match(l)
            if m:
                obj, obj_name = m.group(1), m.group(2).strip()
                continue
            problems.append(f'p{pn} line {ln}: unrecognised: {l.strip()[:70]!r}')
    if problems:
        raise SystemExit('refusing: the page did not read cleanly\n  ' + '\n  '.join(problems))
    if grand is None:
        raise SystemExit('refusing: no GRAND TOTAL read')
    return accounts, totals, grand


def figures(a):
    return [a[k] for k in S.FIGURE_FIELDS]


def tie(accounts, totals, grand):
    fails = []
    for a in accounts:
        unknown = {r['source'] for r in a['lines']} - set(COLUMN_OF)
        if unknown:
            fails.append(f"{a['account']}: unknown sources {sorted(unknown)}")
            continue
        s = defaultdict(Decimal)
        for r in a['lines']:
            if r['fiscal_year'] == '2026':
                s[COLUMN_OF[r['source']]] += Decimal(r['amount'])
        for fig, col in FIG_TO_COL.items():
            if s[col] != a[fig]:
                fails.append(f"{a['account']} {fig}: journal {s[col]} printed {a[fig]}")
        if a['original_approp'] + a['transfers_adjustments'] != a['revised_budget']:
            fails.append(f"{a['account']}: revised does not foot")
        if a['revised_budget'] - a['ytd_actual'] - a['encumbrances'] != a['available_budget']:
            fails.append(f"{a['account']}: available does not foot")
    # A TOTAL line closes the accounts printed since the previous TOTAL of the same depth.
    # Object totals: the accounts of that object. Section totals: the section's accounts.
    for pn, name, figs, end, sec_start in totals:
        cands = []
        for start in range(end - 1, -1, -1):
            got = [sum(x) for x in zip(*[figures(a) for a in accounts[start:end]])]
            cands.append(got)
        if not any(c == figs for c in cands):
            fails.append(f'p{pn} TOTAL {name}: no run of accounts above it sums to {figs}')
    got = [sum(x) for x in zip(*[figures(a) for a in accounts])]
    if got != grand:
        fails.append(f'GRAND TOTAL: accounts sum to {got}, printed {grand}')
    return fails


def tie_other(accounts):
    import json
    from decimal import Decimal as D
    flow = defaultdict(D)
    for a in accounts:
        if a['fund'] != '1500':
            continue
        for r in a['lines']:
            if COLUMN_OF[r['source']] == 'actual':
                flow[(a['side'], r['fiscal_year'])] += D(r['amount'])
    fails = []
    read = [r for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'),
                                           encoding='utf-8'))
            if r['fy'] == '2023' and r['fund'] == 'Park User Fees']
    if len(read) != 1:
        return ['FY2023 Park User Fees row: expected one, found %d' % len(read)], {}
    r = read[0]
    if -flow[('revenue', '2023')] != D(r['receipts']):
        fails.append('FY2023 receipts %s vs annual report %s' % (-flow[('revenue', '2023')], r['receipts']))
    if flow[('expense', '2023')] != D(r['disbursements']):
        fails.append('FY2023 spending %s vs annual report %s' % (flow[('expense', '2023')], r['disbursements']))
    closing = {2023: D(r['carried'])}
    for fy in (2024, 2025, 2026):
        closing[fy] = closing[fy - 1] - flow[('revenue', str(fy))] - flow[('expense', str(fy))]
    fin = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'finance.json'), encoding='utf-8'))
    opening = D(str(fin['measures']['sr-1500']['current']['opening']))
    if closing[2025] != opening:
        fails.append('FY2025 closing by the journal %s vs FY2026 report opening %s' % (closing[2025], opening))
    return fails, closing


def redact(f):
    """Apply the declared mask. Returns the published row's text fields and the masked flag."""
    desc, doc = f['description'], f['doc_no']
    if f['ref_type'] == 'REF' and doc in MASKED_RECEIPTS:
        head = desc.split('/')[0]
        return dict(description=f'{head}/{MASK}', doc_no=MASK), MASKED_RECEIPTS[doc]
    if f['ref_type'] == 'REF' and PERSON_PAYER.search(desc):
        raise SystemExit(f'refusing: receipt {doc} names a person ({desc!r}) and is not in '
                         'MASKED_RECEIPTS -- review it and declare it')
    return dict(description=desc, doc_no=doc), ''


def build(blob):
    accounts, totals, grand = parse(blob)
    fails = tie(accounts, totals, grand)
    more, closing = tie_other(accounts)
    fails += more
    if fails:
        raise SystemExit('refusing: the ties failed\n  ' + '\n  '.join(fails))
    rows, arows = [], []
    for a in accounts:
        for f in a['lines']:
            text, masked = redact(f)
            rows.append({**{k: a[k] for k in ('fund', 'section', 'account', 'object',
                                               'object_name', 'account_description', 'side')},
                         'fund_name': a['section'].split(' ', 1)[1],
                         **{k: f[k] for k in ('fiscal_year', 'period', 'journal',
                                              'effective_date', 'source', 'amount', 'ref_type',
                                              'vendor_no', 'vendor', 'doc_type', 'check_no',
                                              'page', 'line')},
                         'posts_to': COLUMN_OF[f['source']], **text, 'masked': masked})
        arows.append({**{k: a[k] for k in ACCOUNT_FIELDS if k in a and k != 'journal_lines'},
                      'journal_lines': len(a['lines'])})
    return rows, arows, grand, len(totals), closing


def to_csv(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in fields})
    return buf.getvalue()


def main():
    args = sys.argv[1:]
    rows, arows, grand, ntot, closing = build(load_raw())
    outs = {OUT: to_csv(FIELDS, rows), OUT_ACCOUNTS: to_csv(ACCOUNT_FIELDS, arows)}
    if '--review' in args:
        seen = sorted({(r['vendor'], r['description']) for r in rows})
        for v, d in seen:
            print(f'{v:22} | {d}')
        print(f'{len(seen)} distinct vendor/description pairs')
        return
    summary = (f'{len(rows)} journal lines in {len(arows)} accounts; every account, {ntot} '
               f'TOTAL lines and the GRAND TOTAL ({grand[3]} actual) tie; '
               f"{sum(1 for r in rows if r['masked'])} lines masked; fund 1500 FY2023 equals the annual "
               f"report and chains to the FY2026 opening ({closing[2025]})")
    if '--check' in args:
        stale = [p for p, t in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8', newline='').read() != t]
        if stale:
            raise SystemExit('STALE: ' + ', '.join(os.path.relpath(p, ROOT) for p in stale))
        print('ok:', summary)
        return
    for p, t in outs.items():
        with open(p + '.part', 'w', encoding='utf-8', newline='') as fh:
            fh.write(t)
        os.replace(p + '.part', p)
    print('wrote:', summary)


if __name__ == '__main__':
    main()
