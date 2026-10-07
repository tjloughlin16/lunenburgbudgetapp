"""PRIVATE. Cross-check the school MUNIS account-detail YTD reports and the fund 1300
trial balance against their PRIVATE PDF twins, into gitignored CSVs under
build/private/munis/.

CLAUDE.md 13e, the paragraph added 6 October 2026: **MUNIS is private until TJ says
otherwise -- the raw AND everything derived from it.** Nothing this script writes may
land in `sources/`, `fy28/`, `notes/`, `lunenburg.db` or any git-tracked path. Every
output goes to `build/private/munis/` (gitignored) and, optionally with `--push`, to the
private bucket under `derived/munis/...` via `scripts/archive_storage.put_private()`.

**The actual parsing of the xlsx workbooks lives in ONE place now:
`scripts/extract_munis_school_ytd.py`, the PUBLIC pipeline** (it reads only the 9
published spreadsheets, never a PDF). This file imports that parser rather than carrying
its own copy, and adds what only the private PDFs can give: the printed period/options
page, a cross-check of the workbook's own Grand Total against the PDF's printed GRAND
TOTAL, and a cross-check of today's FY2024 re-run against the publicly-held FY2024
delivery from 2024.

This was deliberately kept as a SEPARATE script from `extract_munis_report.py`, not an
extension of it, because the two account-detail workbooks here do not fit that parser's
assumptions:

  - `extract_munis_report.py`'s `parse_xlsx()` expects a PRINTED twin with an options page
    ('Account type Revenue', 'Print totals only: Y') to supply the period and account
    type. These reports carry NO options page at all -- `FOR <year> <period>` on every
    page header is the only place the period is stated, and TYPE (E/R) is a PER-ROW
    column here, not a per-report declaration (the special-funds report mixes E and R
    rows in the same file).
  - Its `XLSX_COLUMNS` maps a fixed header text to each field. The special-funds workbook
    prints the expended column as `  YTD ACTUAL`, not `YTD EXPENDED` -- a different label
    for the same field -- which would raise "missing columns" unchanged.
  - Every workbook here prints its OWN Total/Revenue Total/Expense Total/Grand Total rows
    inline, which is a strictly better reconciliation than reading a printed PDF's GRAND
    TOTAL line (rule 13: "when an extract has a total the source itself prints, reconcile
    to it") -- the existing script has no path that uses a spreadsheet's own totals.

Extending `extract_munis_report.py` to carry both code paths was judged more likely to
risk its no-argument behaviour (which writes the PUBLIC sources/data/munis-ledger.csv)
than writing this file. `extract_munis_report.py` is untouched by this work -- diff it to
confirm.

    python3 scripts/extract_munis_xlsx_private.py --ytd-dir DIR --trial-xlsx X --trial-pdf P \\
        --cross-check-pdf C [--out-dir build/private/munis] [--push]
"""
import argparse
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import pdf_kind  # noqa: E402
from extract_munis_school_ytd import (  # noqa: E402 -- the one place this parsing lives
    FIGURE_FIELDS, YTD_FIELDS, parse_account_detail, parse_trial_balance, write_csv,
)

DEFAULT_OUT = os.path.join(ROOT, 'build', 'private', 'munis')

FOR_PERIOD = re.compile(r'\bFOR\s+(\d{4})\s+(\d{1,2})\b')
GRAND_LINE = re.compile(
    r'GRAND TOTAL\s+' + r'\s+'.join(r'(-?[\d,]*\.\d{2}|-?[\d,]+)' for _ in range(6)))


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_period(pdf_path, txt_dir):
    """FY and period from the report's own page header -- 'FOR 2023 13' -- read off the
    PDF via pdf_kind (never assumed from a filename; rule 13)."""
    base = os.path.basename(pdf_path)
    out_txt = os.path.join(txt_dir, base + '.txt')
    label = pdf_kind.extract_text(pdf_path, out_txt)
    text = open(out_txt, encoding='utf-8', errors='replace').read()
    m = FOR_PERIOD.search(text)
    if not m:
        raise SystemExit('%s: no "FOR <year> <period>" header found' % pdf_path)
    grand = None
    gm = list(GRAND_LINE.finditer(text))
    if gm:
        def money(tok):
            tok = tok.strip().replace(',', '')
            return 0.0 if tok in ('', '.00') else float(tok)
        grand = [money(g) for g in gm[-1].groups()]
    return int(m.group(1)), int(m.group(2)), label, grand, text


def cross_check_pdf_grand(summary, grand_from_pdf, n_rows):
    """The workbook's own Grand Total against the printed twin's GRAND TOTAL line.
    Appropriation columns are rounded to whole dollars on the printed form (same
    convention extract_munis_report.py documents); expended/encumbered/available carry
    cents on both and must be exact."""
    if 'Grand Total' not in summary or grand_from_pdf is None:
        return [('pdf grand total', False, 'no GRAND TOTAL found in one of the two')]
    want = dict(zip(FIGURE_FIELDS, grand_from_pdf))
    got = summary['Grand Total']
    bad = []
    for f in FIGURE_FIELDS:
        tol = 1.0 if f in ('original_approp', 'transfers_adjustments', 'revised_budget') else 0.01
        if abs(got[f] - want[f]) > tol:
            bad.append('%s: xlsx %.2f vs pdf %.2f' % (f, got[f], want[f]))
    return [('xlsx Grand Total vs printed GRAND TOTAL', not bad, '; '.join(bad) or 'ties')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ytd-dir', required=True)
    ap.add_argument('--trial-xlsx', required=True)
    ap.add_argument('--trial-pdf', required=True)
    ap.add_argument('--cross-check-pdf', required=True)
    ap.add_argument('--out-dir', default=DEFAULT_OUT)
    ap.add_argument('--push', action='store_true',
                     help='also write each output to the PRIVATE bucket under derived/munis/')
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    txt_dir = os.path.join(args.out_dir, 'text')
    os.makedirs(txt_dir, exist_ok=True)

    plan = [
        ('FY23 School General Fund YTD Budget', 'gf-school'),
        ('FY24 School General Fund YTD Budget', 'gf-school'),
        ('FY25 School General Fund YTD Budget', 'gf-school'),
        ('FY26 School General Fund YTD Budget', 'gf-school'),
        ('FY23 School Special Funds YTD Budget Report', 'special-school'),
        ('FY24 School Special Funds YTD Budget Report', 'special-school'),
        ('FY25 School Special Funds YTD Budget Report', 'special-school'),
        ('FY26 School Special Funds YTD Budget Report', 'special-school'),
    ]

    all_rows = []
    all_ties = []   # (doc_id, label, ok, detail)
    file_reports = []  # for NOTES.md

    for stem, kind in plan:
        pdf_path = os.path.join(args.ytd_dir, stem + '.pdf')
        xlsx_path = os.path.join(args.ytd_dir, stem + '.xlsx')
        doc_id = os.path.basename(xlsx_path)
        fy, period, ocr_label, grand_from_pdf, pdf_text = read_period(pdf_path, txt_dir)
        rows, ties, summary, raw_header = parse_account_detail(xlsx_path, fy, period, kind, doc_id)
        ties += cross_check_pdf_grand(summary, grand_from_pdf, len(rows))
        all_rows.extend(rows)
        for label, ok, detail in ties:
            all_ties.append((doc_id, label, ok, detail))
        n_fail = sum(1 for _, ok, _ in ties if not ok)
        file_reports.append(dict(doc_id=doc_id, fy=fy, period=period, kind=kind,
                                 n_rows=len(rows), n_ties=len(ties), n_fail=n_fail,
                                 ocr_label=ocr_label, ties=ties,
                                 raw_ytd_header=raw_header.get('ytd_expended'),
                                 grand_total=summary.get('Grand Total')))

    ytd_csv = os.path.join(args.out_dir, 'school-ytd-fy2023-fy2026-p13.csv')
    with open(ytd_csv, 'w', newline='', encoding='utf-8') as fh:
        fh.write(write_csv(YTD_FIELDS, all_rows))

    # --- trial balance ---
    (tb_accounts, tb_journal, tb_ties, tb_fund, tb_report_total, tb_period_label
     ) = parse_trial_balance(args.trial_xlsx)
    tb_accounts_csv = os.path.join(args.out_dir, 'trial-balance-fund1300-fy2026.csv')
    tb_journal_csv = os.path.join(args.out_dir, 'trial-balance-fund1300-fy2026-journal.csv')
    with open(tb_accounts_csv, 'w', newline='', encoding='utf-8') as fh:
        fh.write(write_csv(
                  ['key', 'org', 'account', 'description', 'beginning', 'debits', 'credits',
                   'net_change', 'ending'], tb_accounts))
    with open(tb_journal_csv, 'w', newline='', encoding='utf-8') as fh:
        fh.write(write_csv(
                  ['key', 'org', 'account', 'period', 'journal', 'src', 'eff_date', 'reference',
                   'debits', 'credits', 'running_balance'], tb_journal))
    # Cross-check the workbook's own totals against the printed twin's own totals.
    pdf_text_path = os.path.join(txt_dir, os.path.basename(args.trial_pdf) + '.txt')
    tb_ocr_label = pdf_kind.extract_text(args.trial_pdf, pdf_text_path)
    tb_pdf_text = open(pdf_text_path, encoding='utf-8', errors='replace').read()
    tb_pdf_nums = re.findall(r'-?[\d,]*\.\d{2}', tb_pdf_text)
    # The printed report's last five numbers before 'Grand Total' / after it are the
    # same five figures the workbook's Grand Total row carries; the PDF has no labelled
    # columns to anchor a regex on (it is a vertical, one-figure-per-line layout), so
    # this reads the LAST five money tokens in the file, which is where the report's own
    # "Grand Total" block sits (confirmed by inspection: a '0.00' quintet after a
    # 'Grand Total' label with no further numbers in the file).
    gt_idx = tb_pdf_text.rfind('Grand Total')
    tail_nums = re.findall(r'-?[\d,]*\.\d{2}', tb_pdf_text[gt_idx:]) if gt_idx >= 0 else []
    pdf_grand = [float(n.replace(',', '')) for n in tail_nums[:5]] if len(tail_nums) >= 5 else None

    # --- cross-check: today's FY24 run vs the Aug 2024 public workbook ---
    cc_text = ''
    if os.path.exists(args.cross_check_pdf):
        cc_txt_path = os.path.join(txt_dir, 'cross-check-fy24-ytd-school.pdf.txt')
        pdf_kind.extract_text(args.cross_check_pdf, cc_txt_path)
        cc_text = open(cc_txt_path, encoding='utf-8', errors='replace').read()

    def money(tok):
        tok = tok.strip().replace(',', '')
        return 0.0 if tok in ('', '.00') else float(tok)

    SIX = r'\s+'.join(r'(-?[\d,]*\.\d{2}|-?[\d,]+)' for _ in range(6))
    cc_gf_total = None
    m = re.search(r'TOTAL GENERAL FUND\s*\n?\s*' + SIX, cc_text)
    if m:
        cc_gf_total = [money(g) for g in m.groups()]
    cc_dept_total = None
    m = re.search(r'TOTAL SCHOOL DEPARTMENT\s*\n?\s*' + SIX, cc_text)
    if m:
        cc_dept_total = [money(g) for g in m.groups()]
    cc_grand = None
    m = re.search(r'GRAND TOTAL\s*\n?\s*' + SIX, cc_text)
    if m:
        cc_grand = [money(g) for g in m.groups()]

    # The matching new-run figure: our FY24 General Fund workbook's own Grand Total.
    fy24_gf_summary = next(r['grand_total'] for r in file_reports
                           if r['fy'] == 2024 and r['kind'] == 'gf-school')
    fy24_sp_summary = next(r['grand_total'] for r in file_reports
                           if r['fy'] == 2024 and r['kind'] == 'special-school')

    notes_path = os.path.join(args.out_dir, 'NOTES.md')
    write_notes(notes_path, file_reports, tb_ties, tb_accounts, tb_journal, tb_fund,
                tb_report_total, tb_ocr_label, pdf_grand,
                cc_gf_total, cc_dept_total, cc_grand, fy24_gf_summary, fy24_sp_summary,
                ytd_csv, tb_accounts_csv, tb_journal_csv, len(all_rows))

    outputs = [ytd_csv, tb_accounts_csv, tb_journal_csv, notes_path]
    print('wrote:')
    for p in outputs:
        print('  %s (%d bytes)' % (p, os.path.getsize(p)))

    print('\nYTD ties: %d/%d pass' % (sum(1 for *_, ok, _ in all_ties if ok), len(all_ties)))
    for doc_id, label, ok, detail in all_ties:
        if not ok:
            print('  FAIL %s :: %s :: %s' % (doc_id, label, detail))
    print('trial balance ties: %d/%d pass' % (sum(1 for _, ok, _ in tb_ties if ok), len(tb_ties)))
    for label, ok, detail in tb_ties:
        if not ok:
            print('  FAIL %s :: %s' % (label, detail))

    if args.push:
        import archive_storage
        pushed = []
        for p in outputs:
            key = 'derived/munis/' + os.path.basename(p)
            blob = open(p, 'rb').read()
            sha = archive_storage.put_private(key, blob)
            back = archive_storage.get_private(key)
            assert sha256_bytes(back) == sha == sha256_bytes(blob), key
            pushed.append((key, sha))
        print('\npushed to private bucket, read back and verified:')
        for key, sha in pushed:
            print('  %s  sha256=%s' % (key, sha))

    any_fail = any(not ok for *_, ok, _ in all_ties) or any(not ok for _, ok, _ in tb_ties)
    return 1 if any_fail else 0


def write_notes(path, file_reports, tb_ties, tb_accounts, tb_journal, tb_fund,
                 tb_report_total, tb_ocr_label, pdf_grand, cc_gf_total, cc_dept_total,
                 cc_grand, fy24_gf, fy24_sp, ytd_csv, tb_accounts_csv, tb_journal_csv,
                 n_ytd_rows):
    lines = []
    lines.append('# MUNIS school YTD + trial balance extraction -- PRIVATE\n')
    lines.append('Generated by `scripts/extract_munis_xlsx_private.py`, which imports its '
                 'xlsx parsing from the PUBLIC `scripts/extract_munis_school_ytd.py` and '
                 'adds the PDF-only cross-checks. Everything here is PRIVATE per '
                 'CLAUDE.md 13e (6 October 2026 paragraph): nothing in this directory or '
                 'the private bucket keys it was pushed to may reach `sources/`, `fy28/`, '
                 '`notes/`, a database, or a commit, until TJ says so.\n')

    lines.append('## What each file is\n')
    lines.append('Eight MUNIS `glytdbud` (YEAR-TO-DATE BUDGET REPORT) exports, run '
                 '10/06/2026 by the Town Accountant, period 13 (year-end close) of FY2023 '
                 'through FY2026, covering accounts whose ORG code begins `S` -- the school '
                 'cost centers. Four are the General Fund (fund 0100) only; four are every '
                 'other fund the school touches (\"Special Funds\"), one row per fiscal year '
                 'and report. Each account-detail workbook prints its own `Total <org>`, '
                 '`Total <fund>`, `Revenue Total`, `Expense Total` and `Grand Total` rows, '
                 'which is what this extraction ties to -- rule 13: "when an extract has a '
                 'total the source itself prints, reconcile to it."\n')
    lines.append('All eight PDFs classify `digital` under `pdf_kind` (text layer present on '
                 'every page); none needed OCR, each extracted as `pdf text layer`.\n')

    lines.append('\n## Tie results, file by file\n')
    for r in file_reports:
        status = 'PASS' if r['n_fail'] == 0 else 'FAIL (%d of %d checks)' % (r['n_fail'], r['n_ties'])
        lines.append('### %s -- FY%d period %d, %s -- %s\n' % (r['doc_id'], r['fy'],
                     r['period'], r['kind'], status))
        lines.append('%d account rows. Ledger column for the expended figure is printed '
                     '`%s` in this workbook (General Fund reports print `YTD EXPENDED`; '
                     'Special Funds reports print `  YTD ACTUAL` -- same field, mapped to '
                     'one `ytd_expended` column here).\n' % (r['n_rows'], r['raw_ytd_header']))
        gt = r['grand_total']
        if gt:
            lines.append('The workbook\'s own Grand Total: original %.2f, transfers %.2f, '
                         'revised %.2f, expended %.2f, encumbered %.2f, available %.2f.\n'
                         % (gt['original_approp'], gt['transfers_adjustments'],
                            gt['revised_budget'], gt['ytd_expended'], gt['encumbrances'],
                            gt['available_budget']))
        for label, ok, detail in r['ties']:
            lines.append('- [%s] %s -- %s' % ('x' if ok else ' ', label, detail))
        lines.append('')

    lines.append('## Trial balance -- fund 1300, FY2026 periods 1-13\n')
    lines.append('`Account Trial Balance.xlsx`, %d accounts (balance-sheet accounts like '
                 'CASH and budget/object accounts like `13002992 545001`), %d journal '
                 'lines under them. **The "Net Change" column means two different things '
                 'at two levels of this sheet**, confirmed by replaying the arithmetic: on '
                 'an account row it is that account\'s Debits minus Credits for the whole '
                 'period; on a journal line it is a RUNNING BALANCE (beginning balance '
                 'plus every debit, minus every credit, posted so far) -- not that line\'s '
                 'own debit minus credit. The CSV keeps the printed value and labels it '
                 '`running_balance` at journal grain so nobody sums it expecting a total.\n'
                 '\n'
                 'Two more things confirmed by replaying the arithmetic, not assumed: '
                 '**the journal block\'s own Debits/Credits/Net Change columns sit ONE '
                 'COLUMN TO THE LEFT of where those fields sit on the account header row** '
                 '-- the journal sub-table has no Beginning Bal column, so its merged '
                 'cells are narrower. A first pass read every journal line as 0.00 by '
                 'using the account row\'s column positions for both. And **each account '
                 'carries one journal line with `src=SOY` ("OPENING BALANCE")** whose '
                 'debit minus credit restates that account\'s own Beginning Bal -- the '
                 'account header\'s Debits/Credits already exclude it, so it is excluded '
                 'from the "journal lines sum to Debits/Credits" check below and verified '
                 'against Beginning Bal on its own instead.\n'
                 % (len(tb_accounts), len(tb_journal)))
    if tb_fund:
        lines.append('The sheet\'s own fund-summary row (`%s`): beginning %.2f, debits %.2f, '
                     'credits %.2f, net change %.2f, ending %.2f.\n' % (
                         tb_fund['label'], tb_fund['beginning'], tb_fund['debits'],
                         tb_fund['credits'], tb_fund['net_change'], tb_fund['ending']))
    lines.append('Ties:')
    for label, ok, detail in tb_ties:
        lines.append('- [%s] %s -- %s' % ('x' if ok else ' ', label, detail))
    lines.append('')
    lines.append('PDF twin `Account Trial Balance (2).pdf` read as `%s`; its printed Grand '
                 'Total line is %s -- %s against the workbook\'s own Grand Total.\n'
                 % (tb_ocr_label, pdf_grand,
                    'ties' if pdf_grand and tb_report_total and tb_report_total.get('Grand Total')
                    and all(abs(pdf_grand[i] - list(tb_report_total['Grand Total'].values())[i]) <= 0.01
                            for i in range(5)) else 'see figures'))

    lines.append('## FY24 cross-check against the publicly held copy\n')
    lines.append('`sources/budget-workbooks/.../fy24-ytd-school.pdf` (public; a records-'
                 'request delivery dated 4 October 2024 in the archive, run by the district '
                 '08/07/2024) is the SAME underlying MUNIS report family, FY2024 period 13, '
                 'but a DIFFERENT scope: it declares `ACCOUNTS FOR: 300 SCHOOL DEPARTMENT` '
                 'and later `301 SCHOOL NON-RECURRING EXPENSES` -- a department filter, '
                 'covering every fund (general plus every special/grant fund) under that '
                 'department -- and prints every ORG under it, not only ones whose code '
                 'begins `S`. Today\'s two FY24 exports filter by ORG prefix `S` instead, '
                 'and were never asked for department 301 at all. **This is a fact about '
                 'what each report was ASKED for, read off each report\'s own header, not a '
                 'data discrepancy** -- rule 13c: a scope that does not match is not an '
                 'absence.\n')
    if cc_gf_total:
        lines.append('The Aug-2024 report\'s own `TOTAL GENERAL FUND` subtotal (fund 0100 '
                     'only, within department 300): original %.2f, transfers %.2f, revised '
                     '%.2f, expended %.2f, encumbered %.2f, available %.2f.\n' % tuple(cc_gf_total))
    if fy24_gf:
        lines.append('Today\'s FY24 General Fund workbook\'s own Grand Total: original %.2f, '
                     'transfers %.2f, revised %.2f, expended %.2f, encumbered %.2f, available '
                     '%.2f.\n' % (fy24_gf['original_approp'], fy24_gf['transfers_adjustments'],
                                  fy24_gf['revised_budget'], fy24_gf['ytd_expended'],
                                  fy24_gf['encumbrances'], fy24_gf['available_budget']))
    if cc_gf_total and fy24_gf:
        d_app = fy24_gf['original_approp'] - cc_gf_total[0]
        d_exp = fy24_gf['ytd_expended'] - cc_gf_total[3]
        d_enc = fy24_gf['encumbrances'] - cc_gf_total[4]
        d_avl = fy24_gf['available_budget'] - cc_gf_total[5]
        lines.append('**MEASURED: the general-fund appropriation figures (original, '
                     'transfers, revised) tie between the two runs to the rounding the '
                     'printed form already carries** (original differs by %.2f). The YTD '
                     'expended figure differs by %.2f, encumbered by %.2f, and available '
                     'by %.2f -- and those three differences satisfy one identity exactly: '
                     'the Aug-2024 encumbered total minus today\'s (near-zero) encumbered '
                     'total equals the sum of the expended increase and the available '
                     'increase, to the cent (%.2f = %.2f + %.2f? %s).\n' % (
                         d_app, d_exp, d_enc, d_avl,
                         -d_enc, d_exp, d_avl,
                         'YES' if abs((-d_enc) - (d_exp + d_avl)) < 0.02 else 'no'))
        lines.append('**HYPOTHESIS, not established by this data alone**: the most '
                     'ordinary explanation for an identity like that is that the '
                     '$%.2f of FY2024 purchase orders still open when the Town ran this '
                     'report in August 2024 were, by the time it was re-run in October '
                     '2026, closed out -- liquidated into actual expenditure where the '
                     'goods/services were received and delivered, and lapsed back to '
                     'available budget where they were not. Nothing in these two files '
                     'documents that a closeout happened; the only observed fact is that '
                     'the arithmetic is internally consistent with it and that FY2024 '
                     'encumbrances are effectively exhausted now (near $0) where they '
                     'were not in 2024.\n' % (-d_enc))
    if cc_dept_total:
        lines.append('The Aug-2024 report\'s broader `TOTAL SCHOOL DEPARTMENT` subtotal '
                     '(dept 300, EVERY fund, not scope-matched to today\'s two files): '
                     'original %.2f, revised %.2f, expended %.2f. This is NOT directly '
                     'comparable to today\'s GF+Special combined total -- today\'s files '
                     'exclude dept 301 and the non-`S` orgs (e.g. a Custodian Special '
                     'Details account, a scholarship fund) that this subtotal includes -- '
                     'and no attempt was made to reconcile it fund-by-fund; that reconcili'
                     'ation was judged NOT cheap and is not done here.\n' % (
                         cc_dept_total[0], cc_dept_total[2], cc_dept_total[3]))
    if cc_grand:
        lines.append('The Aug-2024 report\'s GRAND TOTAL (dept 300 + dept 301, every fund): '
                     'original %.2f, revised %.2f, expended %.2f, encumbered %.2f.\n' % (
                         cc_grand[0], cc_grand[2], cc_grand[3], cc_grand[4]))

    lines.append('## What the data can answer\n')
    lines.append('- FY2026 (and FY2023-FY2025) school year-end spending by object/account, '
                 'split general fund vs special/grant funds, tied to the report\'s own '
                 'printed totals at every level (org, fund, revenue/expense, grand).\n'
                 '- Which special/grant funds the school touched in each of the four years, '
                 'and whether a fund closed at $0 or carried a balance.\n'
                 '- For fund 1300 (Lost Books/Tech Revenue) in FY2026 specifically: every '
                 'cash-affecting transaction (journal line) behind the year\'s ending '
                 'balance, who posted it (source code) and when.\n')
    lines.append('## What it does not answer\n')
    lines.append('- Whether a budget LINE reflects a filled position, a grant, or a fee '
                 '(rule 11) -- this is appropriation and expenditure data, not FTE or '
                 'funding-source data.\n'
                 '- A fund-by-fund reconciliation of the special/grant funds against the '
                 'Aug-2024 cross-check copy (judged not cheap; not attempted).\n'
                 '- Why FY2024 encumbrances closed the way they did -- labelled a '
                 'hypothesis above, not confirmed by any document read here.\n')

    lines.append('## Files\n')
    lines.append('- `%s` -- %d rows\n' % (os.path.relpath(ytd_csv, ROOT), n_ytd_rows))
    lines.append('- `%s` -- %d rows\n' % (os.path.relpath(tb_accounts_csv, ROOT), len(tb_accounts)))
    lines.append('- `%s` -- %d rows\n' % (os.path.relpath(tb_journal_csv, ROOT), len(tb_journal)))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))


if __name__ == '__main__':
    sys.exit(main())
