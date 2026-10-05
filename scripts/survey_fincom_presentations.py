#!/usr/bin/env python3
"""Survey of Finance Committee tasks I1-I4: do these ~155 presentations, memos, Q&As and
impact statements (FY2021-FY2027) carry a TABLE OF FIGURES that none of the structured
datasets built today already holds?

This is a SURVEY, not a transcription (rule 15 scope: check each document once). It writes
one row per document to `sources/data/fincom-presentation-survey.csv`:

    task, delivered_as, key, pages, has_table, what_the_table_holds, fiscal_years,
    already_captured_by, candidate_for_extraction, why

METHOD, and what each field is actually derived from (rule 13: cite the instrument).

- **has_table** comes from the document's OWN extracted text (`text/<name>.<ext>.txt`,
  already produced by the archive's extractors), never from the filename or folder. Three
  independent signals, any one of which is enough:
    1. a RUN of 4+ consecutive numeric-only lines -- how a table comes out when an
       extractor walks a slide or a Word table cell by cell (seen in the Police FY26 deck:
       "Calls for Service / 26,063 / 27,156 / ..." one figure per line);
    2. a row with 3+ numeric fields on ONE line, comma- or tab-separated -- how a
       spreadsheet sheet dump or a PDF that preserved column spacing reads;
    3. DOLLAR-figure density across the whole document (>= 8 distinct `$` amounts) --
       catches narrative memos that are mostly prose but carry a real figures grid
       somewhere the first two signals miss (e.g. a one-row cost table inside a Q&A).
  A PDF that still reads as table-free is then checked against `pdf_kind.classify()` on
  the ACTUAL PDF (not the text layer) for picture, outline or unreadable pages -- rule 13d.
  If any such page exists, the verdict is `unknown (picture page)`, never `no`: the text
  layer cannot see what is drawn as an image, and 13c forbids reporting that absence as a
  fact about the document.

- **already_captured_by** is NOT a content guess. It is read off the datasets' OWN
  source-file columns (`source_file`, `file`, `version`, `report_key`, `sheet_or_location`
  -- whichever a given CSV carries) in the fifteen datasets named in the task. A direct
  path hit means the dataset was built from this exact document. None of the I1-I4
  documents hit directly -- expected, since tasks A-H already consumed the documents those
  datasets draw on, and I1-I4 is specifically the remaining, unexamined backlog.
  [ASSUMING] a SIBLING hit -- this document sits in the identical directory as a document
  a dataset cites -- is treated as "the same submission, same department, same fiscal
  year" and is recorded too, with `already_captured_by` noting it is a sibling-folder
  inference rather than a literal source match. Wrong case: a background/legal PDF (a
  bylaw, a trust-fund application) sharing a folder with a figures workbook would be
  wrongly suppressed if it also carried its own table -- so the sibling signal only
  SUPPRESSES candidacy; it never overrides a real has_table=yes into a 'no'.

- **fiscal_years** is regex-extracted from the document's own text (`FY ?20\d\d`,
  `Fiscal Year 20\d\d`, `20\d\d-20\d\d`/`20\d\d/\d\d` ranges) -- never assumed from the
  folder (`FY26 Budget/...`) even though the folder is usually right, per rule 13's
  "cite the coordinate, not the folder name" and 13c's point that layouts and content vary
  document to document within one folder.

- **pages**: an exact PDF page count from `pdf_kind.classify()` (the two-reader count,
  rule 13d); an exact sheet count for `.xlsx`/`.xlsm` (count of `===SHEET ...===`
  markers the extractor already writes); `n/a (not paginated in extract)` for `.pptx`,
  `.pptm` and `.docx` -- this archive's text extraction for those formats does not mark
  slide or page boundaries, and claiming a slide count without reading one would be typing
  a figure nobody derived (rule 2); `1` for the lone `.png`.

candidate_for_extraction=yes requires has_table=yes AND no already_captured_by hit. A
picture-page `unknown` is never auto-promoted to a candidate -- the text survey has no
evidence either way, and whether it is worth OCR'ing is a judgement call noted in `why`.

Usage:
    python3 scripts/survey_fincom_presentations.py            # write the survey
    python3 scripts/survey_fincom_presentations.py --check    # assert one row per document,
                                                               #   and that every extracted
                                                               #   table in
                                                               #   fincom-presentation-tables.csv
                                                               #   ties to its printed total
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_kind  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_DOCS = os.path.join(ROOT, 'sources/data/finance-committee-task-docs.csv')
OUT_SURVEY = os.path.join(ROOT, 'sources/data/fincom-presentation-survey.csv')
OUT_TABLES = os.path.join(ROOT, 'sources/data/fincom-presentation-tables.csv')
TASKS = ('I1', 'I2', 'I3', 'I4')

# The structured datasets this survey must not duplicate, and the columns in each that
# might carry a path back to a source document.
DATASETS = {
    'gl-history': 'sources/data/gl-history.csv',
    'omnibus-history': 'sources/data/omnibus-history.csv',
    'town-budget-fy26-fy27': 'sources/data/town-budget-fy26-fy27.csv',
    'town-budget-versions': 'sources/data/town-budget-versions.csv',
    'fincom-ledgers': 'sources/data/fincom-ledgers.csv',
    'eoyr-nss': 'sources/data/eoyr-nss.csv',
    'eoyr-schedule1': 'sources/data/eoyr-schedule1.csv',
    'eoyr-schedule3': 'sources/data/eoyr-schedule3.csv',
    'school-target-fy26': 'sources/data/school-target-fy26.csv',
    'school-staff-fte': 'sources/data/school-staff-fte.csv',
    'capital-requests': 'sources/data/capital-requests.csv',
    'debt-service-projections': 'sources/data/debt-service-projections.csv',
    'fund-balances-fincom': 'sources/data/fund-balances-fincom.csv',
    'opeb-valuations': 'sources/data/opeb-valuations.csv',
    'police-expended': 'sources/data/police-expended.csv',
    'department-budgets-fincom-fy27': 'sources/data/department-budgets-fincom-fy27.csv',
    'public-safety-staffing-plans': 'sources/data/public-safety-staffing-plans.csv',
}
PATH_COLS = ('source_file', 'file', 'version', 'report_key', 'sheet_or_location')
EXT_RE = re.compile(r'[^\s":|]+\.(pdf|xlsx|xlsm|pptx|pptm|csv|docx|xls)', re.I)

NUMERIC_LINE_RE = re.compile(r'^\(?-?\$?\s?[\d][\d,]*(\.\d+)?\)?%?$')
GRID_ROW_RE = re.compile(r'(?:^|[,\t])\s*\$?-?\(?[\d][\d,]*(\.\d+)?\)?\s*(?:[,\t]|$)')
CURRENCY_RE = re.compile(r'\$\s?-?\(?[\d][\d,]*(\.\d+)?\)?')
FY_RE = re.compile(r'\bFY\s?-?\s?(20\d{2}|\d{2})\b', re.I)
FISCAL_YEAR_WORD_RE = re.compile(r'\bFiscal\s+Year\s+(20\d{2})\b', re.I)
YEAR_RANGE_RE = re.compile(r'\b(20\d{2})\s?[-/]\s?(20\d{2}|\d{2})\b')
BARE_YEAR_RE = re.compile(r'\b(20[0-3]\d)\b')


def norm_path(p):
    """A dataset's own citation of a source file, normalized to compare against a key in
    finance-committee-task-docs.csv: strip the 'sources/' prefix, collapse a 'text/'
    extraction subdirectory, drop a '.redacted' marker and the '.txt' extraction suffix."""
    p = p.strip().strip('"')
    p = re.sub(r'^sources/', '', p)
    p = re.sub(r'(^|/)text/', '/', p)
    p = re.sub(r'\.redacted\.', '.', p)
    p = re.sub(r'\.txt$', '', p)
    return p.lower()


STOPWORDS = {
    'fy', 'budget', 'department', 'presentation', 'presentations', 'final', 'draft', 'revised',
    'copy', 'rev', 'updated', 'fincom', 'fincomm', 'town', 'committee', 'school', 'for', 'the',
    'and', 'to', 'of', 'public', 'hearing', 'working', 'request', 'pdf', 'xlsx', 'xlsm', 'pptx',
    'pptm', 'docx', 'doc', 'plan', 'report', 'summary', 'questions', 'answers', 'q', 'a',
}


def content_tokens(basename):
    """Significant words in a filename, with fiscal-year/boilerplate noise removed -- so two
    filenames in the same meeting folder but about different departments ('COA' vs 'Land
    Use') are not treated as the same subject just because they share a folder."""
    stem = os.path.splitext(os.path.basename(basename))[0].lower()
    tokens = re.findall(r'[a-z]+', stem)
    return {t for t in tokens if len(t) >= 4 and t not in STOPWORDS and not t.startswith('fy')}


def build_dataset_index():
    """file_index: normalized path -> {dataset names that cite it directly}.
    dir_index: normalized directory -> {dataset name: {basenames the dataset cites there}}."""
    file_index = {}
    for name, relpath in DATASETS.items():
        path = os.path.join(ROOT, relpath)
        if not os.path.exists(path):
            print(f'WARNING: dataset not found, skipping from survey: {relpath}', file=sys.stderr)
            continue
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            cols = [c for c in PATH_COLS if c in (reader.fieldnames or [])]
            for row in reader:
                for col in cols:
                    for m in EXT_RE.finditer(row.get(col) or ''):
                        file_index.setdefault(norm_path(m.group(0)), set()).add(name)
    dir_index = {}
    for path, names in file_index.items():
        d = os.path.dirname(path)
        for n in names:
            dir_index.setdefault(d, {}).setdefault(n, set()).add(os.path.basename(path))
    return file_index, dir_index


def sibling_matches(key, dir_index):
    """Dataset names with a sibling file in this document's EXACT directory AND sharing at
    least one significant filename token with it -- e.g. 'land-use-fy23-budget.xlsx' matches
    'Land use Department Budget FY23.pptx' (shared token 'land'/'use') but NOT 'FY24 COA
    Budget Presentation.pptx' in the same meeting-date folder, which is a different
    department bundled into the same folder by meeting date, not by subject."""
    d = os.path.dirname(norm_path(key))
    names_in_dir = dir_index.get(d, {})
    my_tokens = content_tokens(key)
    hits = set()
    for name, basenames in names_in_dir.items():
        for b in basenames:
            if content_tokens(b) & my_tokens:
                hits.add(name)
                break
    return hits


def find_text_path(key):
    full = os.path.join(ROOT, 'sources', key)
    d = os.path.dirname(full)
    b = os.path.basename(full)
    txt = os.path.join(d, 'text', b + '.txt')
    return txt if os.path.exists(txt) else None


def extract_fiscal_years(text, delivered_as):
    """Fiscal years named IN THE DOCUMENT's own text -- never assumed from the folder."""
    years = set()
    for m in FY_RE.finditer(text):
        y = m.group(1)
        y = ('20' + y) if len(y) == 2 else y
        if 2005 <= int(y) <= 2030:
            years.add(int(y))
    for m in FISCAL_YEAR_WORD_RE.finditer(text):
        years.add(int(m.group(1)))
    for m in YEAR_RANGE_RE.finditer(text):
        y1 = int(m.group(1))
        y2raw = m.group(2)
        y2 = int(y2raw) if len(y2raw) == 4 else int(str(y1)[:2] + y2raw)
        if 2005 <= y1 <= 2030:
            years.add(y1)
        if 2005 <= y2 <= 2030:
            years.add(y2)
    if not years:
        # Fall back to bare 4-digit years only when nothing FY-labelled was found at all,
        # and only ones that look like fiscal/calendar years in range, not account codes.
        for m in BARE_YEAR_RE.finditer(text):
            y = int(m.group(1))
            if 2010 <= y <= 2029:
                years.add(y)
    return ','.join(str(y) for y in sorted(years))


def longest_numeric_run(lines):
    best, cur = 0, 0
    best_start = cur_start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if NUMERIC_LINE_RE.match(s):
            if cur == 0:
                cur_start = i
            cur += 1
            if cur > best:
                best, best_start = cur, cur_start
        else:
            cur = 0
    return best, best_start


def header_snippet(lines, start_idx, window=4):
    """Short, non-numeric context immediately before a detected numeric run, as a
    human-readable guess at what the table holds. Truncated; never typed from memory."""
    out = []
    i = start_idx - 1
    while i >= 0 and len(out) < window:
        s = lines[i].strip()
        if s and not NUMERIC_LINE_RE.match(s):
            out.append(s)
        elif s:
            break
        i -= 1
    out.reverse()
    snippet = ' / '.join(out)
    return (snippet[:97] + '...') if len(snippet) > 100 else snippet


def detect_grid_rows(text):
    rows = [l for l in text.splitlines() if len(GRID_ROW_RE.findall(l)) >= 3]
    return rows


def detect_table(text, ext, full_path):
    """Returns (has_table, what_the_table_holds, evidence_note)."""
    lines = text.splitlines()
    run_len, run_start = longest_numeric_run(lines)
    grid_rows = detect_grid_rows(text)
    dollar_count = len(CURRENCY_RE.findall(text))

    if run_len >= 4:
        what = header_snippet(lines, run_start) or '(figures grid; no header line found nearby)'
        return 'yes', what, f'{run_len}-line run of numeric-only lines (cell-by-cell table dump)'
    if len(grid_rows) >= 2:
        what = grid_rows[0][:100]
        return 'yes', what, f'{len(grid_rows)} rows with 3+ numeric fields on one line'
    if dollar_count >= 8:
        # Grab the densest line as a representative snippet.
        best_line = max((l for l in lines if '$' in l), key=lambda l: len(CURRENCY_RE.findall(l)),
                         default='')
        return 'yes', best_line.strip()[:100], f'{dollar_count} distinct $ figures in the document'

    # No table signal in the text layer. For a PDF, check whether a picture/outline page
    # could be hiding one (rule 13d) before calling it 'no'.
    if ext == '.pdf' and full_path and os.path.exists(full_path):
        try:
            k = pdf_kind.classify(full_path)
            picture_pages = [p['page'] for p in k['pages']
                             if p['kind'] in ('image', 'text, unreadable', 'outlines')]
            if picture_pages:
                pages_str = ','.join(str(p) for p in picture_pages[:10])
                more = '...' if len(picture_pages) > 10 else ''
                return ('unknown (picture page)', '',
                        f"pdf_kind verdict={k['verdict']}; picture/unreadable pages {pages_str}{more} "
                        f"not reached by the text layer")
        except Exception as e:
            return ('unknown (picture page)', '', f'pdf_kind could not classify: {e}')
    return 'no', '', (f'{dollar_count} $ figures, longest numeric run {run_len} lines, '
                      f'{len(grid_rows)} grid-like rows -- below the table threshold')


def load_task_docs():
    with open(TASK_DOCS, newline='', encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh) if r['task'] in TASKS]
    skipped = [r for r in rows if r['disposition'] == 'withheld']
    kept = [r for r in rows if r['disposition'] != 'withheld']
    for r in skipped:
        print(f"SKIPPING withheld document: {r['task']} {r['key']}", file=sys.stderr)
    return kept


def survey():
    file_index, dir_index = build_dataset_index()
    docs = load_task_docs()
    out_rows = []
    for r in docs:
        task, delivered_as, key = r['task'], r['delivered_as'], r['key']
        full_path = os.path.join(ROOT, 'sources', key)
        ext = os.path.splitext(key)[1].lower()
        norm_key = norm_path(key)

        text_path = find_text_path(key)
        if text_path:
            with open(text_path, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
        else:
            text = ''

        # pages
        if ext == '.pdf' and os.path.exists(full_path):
            try:
                k = pdf_kind.classify(full_path)
                pages = str(len(k['pages']))
            except Exception as e:
                pages = f'error ({e})'
        elif ext in ('.xlsx', '.xlsm'):
            n_sheets = len(re.findall(r'^===SHEET .*===$', text, re.M))
            pages = f'{n_sheets} sheets' if n_sheets else 'n/a (no sheet markers found)'
        elif ext == '.png':
            pages = '1'
        else:
            pages = 'n/a (not paginated in extract)'

        if not text and ext not in ('.png',):
            has_table, what, note = 'unknown (picture page)', '', 'no extracted text found for this document'
        elif ext == '.png':
            has_table, what, note = 'no', '', 'image file read directly; a 2-column text list (Section, Description), no $ figures'
        else:
            has_table, what, note = detect_table(text, ext, full_path if ext == '.pdf' else None)

        fiscal_years = extract_fiscal_years(text, delivered_as) if text else ''

        already = set()
        if norm_key in file_index:
            already |= file_index[norm_key]
        sibling_names = sibling_matches(key, dir_index)
        sibling_note = ''
        if sibling_names and has_table in ('yes', 'unknown (picture page)'):
            already |= {f'{n} (sibling-folder inference)' for n in sibling_names}
            sibling_note = ' -- same folder as a document that dataset was built from'

        candidate = 'yes' if (has_table == 'yes' and not already) else 'no'
        if has_table == 'yes' and already:
            why = f'table present but {", ".join(sorted(already))} already covers this folder{sibling_note}'
        elif has_table == 'yes':
            why = note
        elif has_table == 'unknown (picture page)':
            why = f'text layer has no table; {note}'
        else:
            why = note

        out_rows.append({
            'task': task,
            'delivered_as': delivered_as,
            'key': key,
            'pages': pages,
            'has_table': has_table,
            'what_the_table_holds': what,
            'fiscal_years': fiscal_years,
            'already_captured_by': '; '.join(sorted(already)),
            'candidate_for_extraction': candidate,
            'why': why,
        })
    return out_rows


def write_survey(rows):
    fieldnames = ['task', 'delivered_as', 'key', 'pages', 'has_table', 'what_the_table_holds',
                  'fiscal_years', 'already_captured_by', 'candidate_for_extraction', 'why']
    with open(OUT_SURVEY, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def check():
    docs = load_task_docs()
    doc_keys = {r['key'] for r in docs}
    if not os.path.exists(OUT_SURVEY):
        print('FAIL: survey CSV does not exist; run without --check first', file=sys.stderr)
        return False
    with open(OUT_SURVEY, newline='', encoding='utf-8') as fh:
        survey_rows = list(csv.DictReader(fh))
    survey_keys = [r['key'] for r in survey_rows]
    ok = True
    if len(survey_keys) != len(set(survey_keys)):
        from collections import Counter
        dupes = [k for k, c in Counter(survey_keys).items() if c > 1]
        print(f'FAIL: {len(dupes)} key(s) have more than one survey row: {dupes[:5]}', file=sys.stderr)
        ok = False
    missing = doc_keys - set(survey_keys)
    extra = set(survey_keys) - doc_keys
    if missing:
        print(f'FAIL: {len(missing)} I1-I4 document(s) have no survey row: {sorted(missing)[:5]}',
              file=sys.stderr)
        ok = False
    if extra:
        print(f'FAIL: {len(extra)} survey row(s) reference a document not in I1-I4: {sorted(extra)[:5]}',
              file=sys.stderr)
        ok = False
    if ok:
        print(f'OK: every one of {len(doc_keys)} I1-I4 documents has exactly one survey row.')

    ok2 = check_tables_tie()
    return ok and ok2


def check_tables_tie():
    if not os.path.exists(OUT_TABLES):
        print('OK: no fincom-presentation-tables.csv yet (nothing to tie).')
        return True
    with open(OUT_TABLES, newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print('OK: fincom-presentation-tables.csv is empty.')
        return True

    def to_num(v):
        v = (v or '').strip().replace('$', '').replace(',', '')
        neg = v.startswith('(') and v.endswith(')')
        v = v.strip('()')
        if v in ('', '-'):
            return None
        try:
            n = float(v)
        except ValueError:
            return None
        return -n if neg else n

    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[(r['document'], r.get('page/slide', r.get('page_or_slide', '')), r['table_title'])].append(r)

    ok = True
    for (doc, page, title), grp in groups.items():
        total_rows = [r for r in grp if re.search(r'\btotal(s)?\b', r['row_label'], re.I)
                      and not re.search(r'subtotal', r['row_label'], re.I)]
        # A '(subtotal)' row (e.g. "Salaries (subtotal)") is itself the sum of other rows
        # already in this group -- including it in the summed data rows would double-count
        # against the grand total. It is recorded for reference but excluded from the tie.
        subtotal_rows = [r for r in grp if re.search(r'subtotal', r['row_label'], re.I)]
        data_rows = [r for r in grp if r not in total_rows and r not in subtotal_rows]
        if not total_rows:
            print(f"NOTE: no printed total row for '{title}' in {doc} p/s {page} -- "
                  f"nothing to tie, {len(grp)} figures recorded as-is.")
            continue
        for col in {r['column_label'] for r in total_rows}:
            if '%' in col:
                # A percentage column is a ratio, not an amount -- it is never the sum of
                # the rows above it (22.21% + 0% + 0% is not 8.99%), so there is nothing to
                # tie. Only $ / count columns are checked here.
                print(f"NOTE: '{title}' in {doc} p/s {page}, column '{col}' is a percentage -- "
                      f"not additive, not tie-checked.")
                continue
            printed_totals = [to_num(r['value']) for r in total_rows if r['column_label'] == col]
            printed_totals = [t for t in printed_totals if t is not None]
            if not printed_totals:
                continue
            printed_total = printed_totals[0]
            summed = sum(to_num(r['value']) or 0 for r in data_rows if r['column_label'] == col)
            if abs(summed - printed_total) > 0.015 * max(abs(printed_total), 1):
                print(f"FAIL: '{title}' in {doc} p/s {page}, column '{col}': rows sum to "
                      f"{summed:,.2f} but the printed total is {printed_total:,.2f}",
                      file=sys.stderr)
                ok = False
            else:
                print(f"OK: '{title}' in {doc} p/s {page}, column '{col}' ties: "
                      f"{summed:,.2f} == {printed_total:,.2f}")
    return ok


# ---------------------------------------------------------------------------------------
# HAND-EXTRACTED TABLES, from the 7 candidate_for_extraction=yes documents that carry the
# most budget-relevant figures and tie cleanly to a printed total. Every value below was
# read from this document's OWN extracted text (cited coordinate: PDF page, or an exact
# PowerPoint slide number resolved from ppt/presentation.xml's own slide order, not the
# file's on-disk slideN.xml numbering -- rule 13: cite the coordinate, not an instrument's
# guess at it). Column order for the two 8-column decks (IT, Finance Committee) was PROVEN
# by the subtotal arithmetic, not read off the header text, because the header run's
# left-to-right extraction order did not match the data rows' order for the IT deck (rule
# 13b: a position is not a name until something proves it).
#
# A '(subtotal)' row is a printed intermediate sum already covered by the line items above
# it; it is recorded but excluded from the automatic tie-check (see check_tables_tie).
EXTRACTED_TABLES = []


def _rows(document, page, title, columns, data):
    """data: {row_label: [values aligned to `columns`]}."""
    for label, values in data.items():
        for col, val in zip(columns, values):
            EXTRACTED_TABLES.append({'document': document, 'page_or_slide': page,
                                     'table_title': title, 'row_label': label,
                                     'column_label': col, 'value': val})


# --- 1. "FY 2027 Local Receipts" -- updated-budget-fincom-3.26.27.pptx, slide 4 (I4) -----
# Slide title states the FY27 total ($3,535,524); it is not printed as a grid row, so it is
# recorded here as a row of its own, sourced to the title rather than a table cell.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/updated-budget-fincom-3.26.27.pptx', 4,
    'FY 2027 Local Receipts',
    ['FY25 Actual', 'FY26 Budget', 'FY27 Budget'],
    {
        'Motor Vehicle Excise': ['2190195.56', '1875000', '1950000'],
        'Meal & Cannabis Excise': ['160458.23', '125000', '125000'],
        'Penalties/Interest on Taxes and Excises': ['141872.02', '140000', '140000'],
        'PILOT': ['1605.75', '1600', '1600'],
        'Fees': ['202017.87', '180000', '180000'],
        'Dept. Revenue- Schools (Pre-School Tuition, Parking, Special Education Reimbursement)':
            ['183945.08', '61411', '61411'],
        'Dept. Revenue Cemetery Burials': ['3800.00', '3500', '3500'],
        'Other Departmental Revenue (Ambulance)': ['481173.92', '275000', '275000'],
        'Licenses/Permits': ['353444.01', '350000', '350000'],
        'Special Assessments (Trailer Parks)': ['26592.00', '12000', '12000'],
        'Fines and Forfeits': ['17432.57', '12013', '12013'],
        'Investment Income': ['588996.51', '100000', '200000'],
        'Misc. Non-Recurring (Sale of Property, Net Metering Credits, Meadow Woods P&I)':
            ['280843.25', '225000', '225000'],
        'TOTAL (printed in slide title, not a grid row)': ['', '', '3535524'],
    })

# --- 2. "FY 2027 Expenditure Summary" -- same deck, slide 9 (also repeated verbatim on ---
# slides 19 and 47; slide 9 is the first occurrence and is what is cited). "Balanced
# 3.26.26" ties exactly to the revenue side's "Total Revenues Available for Appropriation:
# $49,925,699.99" stated independently on slide 5 of the same deck.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/updated-budget-fincom-3.26.27.pptx', 9,
    'FY 2027 Expenditure Summary',
    ['FY25 Budget', 'FY25 Actual', 'FY26 Budget', 'FY27 Preliminary', 'Balanced 3.26.26',
     'Tier 1', 'Tier 2'],
    {
        'Maturing Debt': ['2941321.50', '2941321.50', '2547440.36', '2537578.36', '2537578.36',
                          '2537578.36', '2537578.36'],
        'General Government Unclassified': ['3879254.21', '3489708.96', '4107709.13',
                                            '4312004.12', '4494862.61', '4550424.59', '4675424.59'],
        'General Government': ['2752295.15', '2234013.96', '2962263.14', '3205051.24',
                               '3137898.64', '3190641.20', '3220907.97'],
        'Public Safety': ['4481172.66', '4222405.73', '4547849.28', '5118965.26', '4810579.33',
                          '4969309.80', '5312329.72'],
        'DPW': ['2703652.09', '2884846.15', '2476953.29', '2807177.51', '2188527.18',
               '2554677.51', '2554677.51'],
        'Facilities and Buildings': ['992711.12', '1024973.60', '1067396.40', '1203408.16',
                                     '1017174.56', '1083494.10', '1127574.56'],
        'Human Services': ['456731.74', '411404.60', '478242.76', '480162.04', '452565.11',
                           '475965.85', '475965.85'],
        'Schools': ['26109022.00', '25611971.71', '27121995.00', '30115565.00', '28024714.07',
                   '29624714.07', '29973241.07'],
        'Culture and Recreation': ['591989.77', '608551.50', '639036.76', '662162.24',
                                   '598960.20', '661168.24', '661168.24'],
        'Intergovernmental': ['2132169.76', '2132169.76', '2397049.98', '2635339.93',
                             '2635339.93', '2635339.93', '2635339.93'],
        'Tax Title': ['29000.00', '7144.13', '30500.00', '30500.00', '27500.00', '27500.00',
                     '27500.00'],
        'Total': ['47069320.00', '45568511.60', '48376436.10', '53107913.86', '49925699.99',
                 '52310813.66', '53201707.81'],
    })

# --- 3. Monty Tech "State and Federal Entitlement Grants", FY2025 -- -----------------------
# monty-tech-school-fy26-budget-presentation-lunenburg-030625.pdf, PDF page 3 (I3)
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'monty-tech-school-fy26-budget-presentation-lunenburg-030625.pdf', 3,
    'FY2025 State and Federal Entitlement Grants (Monty Tech)',
    ['Amount'],
    {
        'Strengthening Career and Technical Education for the 21st Century Act, Perkins V': ['312607'],
        'Title I, Part A Basic Grants to LEAs': ['272731'],
        'Fund Code 240 - IDEA, Part B': ['420925'],
        'Title II, Part A: Supporting Effective Instruction': ['35040'],
        'Title IV, Part A: Student Support and Academic Enrichment': ['21588'],
        'District Total': ['1062891'],
    })

# --- 4. "PACC Anticipated Income FY25" -- fincomm-pres-25-final.pptm, slide 12 (I2) --------
# The slide prints TWO totals over the same three line items: 'Total>>' over all three, and
# 'Total for Ops>>' over the two that are not reserved for capital. Recorded as two table
# groups (same slide, different titles) so each ties to its own printed total rather than
# one checker trying to reconcile two totals against one set of rows.
_rows(
    'budget-workbooks/finance-committee/fy25-budget/public-access-cable/fincomm-pres-25-final.pptm',
    12, 'PACC Anticipated Income FY25 -- all sources',
    ['FY25'],
    {'Comcast': ['194304'], 'Regular Interest': ['13499'], 'Bond Interest (reserved for capital)': ['30960'],
     'Total>>': ['238763']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/public-access-cable/fincomm-pres-25-final.pptm',
    12, 'PACC Anticipated Income FY25 -- operations only',
    ['FY25'],
    {'Comcast': ['194304'], 'Regular Interest': ['13499'], 'Total for Ops>>': ['207803']})

# --- 5. IT Department FY27 budget by line -- presentation-budget-presentation-it- ---------
# preliminary-final-2.26.26.pptx, slide 6 (I4). Column order (FY27 Requested, FY27 $,
# FY27 %) was proven by the Salaries/Expenses subtotal arithmetic, which only closes in
# that order -- the header text, extracted separately, read '...FY27 %, FY27 $'. 'Total IT'
# FY27 Requested ($535,459.33) also matches the slide's separately-stated headline figure
# "Total FY27 Budget Request: $535,459.33".
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/'
    'presentation-budget-presentation-it-preliminary-final-2.26.26.pptx', 6,
    'IT Department FY27 Budget',
    ['FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY25 Actual', 'FY26 Budget',
     'FY27 Requested', 'FY27 $', 'FY27 %'],
    {
        'Tech Support Salaries': ['76432.20', '80028.00', '79030.80', '0.00', '0.00', '0.00',
                                  '0.00', '0'],
        'Tech Admin Support Salaries': ['24529.15', '25314.04', '25516.30', '28821.80',
                                        '48655.36', '59459.33', '10803.97', '22.21'],
        'P/R Remote Meeting Coord.': ['5000.00', '0.00', '1580.62', '0.00', '0.00', '0.00',
                                      '0.00', '0'],
        'Salaries (subtotal)': ['105961.35', '105342.04', '106127.72', '28821.80', '48655.36',
                                '59459.33', '10803.97', '22.21'],
        'Hardware Maintenance': ['70500.00', '54124.47', '53500.00', '41217.68', '38500.00',
                                 '38500.00', '0.00', '0'],
        'Telephone Charges (formerly in Central Purchasing)': ['40000.00', '50211.34', '40000.00',
                                                                '53235.45', '40000.00', '56500.00',
                                                                '16500.00', '41.25'],
        'Purchase of Service (inc. Internet & Website)': ['201420.00', '191912.83', '212594.53',
                                                           '190733.73', '204871.06', '240000.00',
                                                           '35128.94', '17.15'],
        'Contracted Services': ['25000.00', '32641.85', '25000.00', '132407.57', '159285.00',
                                '141000.00', '-18285.00', '-11.48'],
        'Expenses (subtotal)': ['336920.00', '328890.49', '331094.53', '417594.43', '442656.06',
                                '476000.00', '33343.94', '7.53'],
        'Total IT': ['442881.35', '434232.53', '437222.25', '446416.23', '491311.42',
                    '535459.33', '44147.91', '8.99'],
    })

# --- 6. Finance Committee FY27 budget -- draft-fy-27-general-govrernment-budget- -----------
# presentation-budget-presentation-3.12.26.pptx, slide 3 (I4). FY2027 total ($1,575.00)
# matches the slide's own headline "Finance Committee- $1,575".
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/general-government/'
    'draft-fy-27-general-govrernment-budget-presentation-budget-presentation-3.12.26.pptx', 3,
    'Finance Committee FY27 Budget',
    ['FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY25 Actual', 'FY26 Budget', 'FY2027',
     '$ Change', '% Change'],
    {
        'Advertising': ['100.00', '97.35', '100.00', '90.00', '100.00', '125.00', '25.00', '25'],
        'Dues/Membership': ['200.00', '190.00', '200.00', '196.00', '200.00', '200.00', '0.00', '0'],
        'Meetings/School': ['1000.00', '1326.42', '1500.00', '214.27', '1500.00', '1250.00',
                            '-250.00', '-16.67'],
        'TOTAL - FINANCE COMMITTEE': ['1300.00', '1613.77', '1800.00', '500.27', '1800.00',
                                      '1575.00', '-225.00', '-12.50'],
    })

# --- 7. "FY27 Budget Summary" -- school-dept-working-copy-of-fy-27-budget-presentation- ----
# to-finance-committee-r2.pdf, PDF pages 49-50 (I4). Salaries + Expenses = $28,454,841, one
# dollar over the printed Total FY27 Budget of $28,454,840 -- a one-dollar rounding
# difference (within the 1.5% tolerance this checker applies), noted rather than hidden.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/school-department/'
    'school-dept-working-copy-of-fy-27-budget-presentation-to-finance-committee-r2.pdf', '49-50',
    'FY27 Budget Summary',
    ['Amount'],
    {
        'Salaries': ['18869757'],
        'Expenses': ['9585084'],
        'Total FY27 Budget': ['28454840'],
    })


def write_tables():
    fieldnames = ['document', 'page_or_slide', 'table_title', 'row_label', 'column_label', 'value']
    with open(OUT_TABLES, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in EXTRACTED_TABLES:
            if r['value'] != '':
                w.writerow(r)


if __name__ == '__main__':
    if '--check' in sys.argv:
        sys.exit(0 if check() else 1)
    rows = survey()
    write_survey(rows)
    write_tables()
    n_table = sum(1 for r in rows if r['has_table'] == 'yes')
    n_unknown = sum(1 for r in rows if r['has_table'].startswith('unknown'))
    n_captured = sum(1 for r in rows if r['already_captured_by'])
    n_candidate = sum(1 for r in rows if r['candidate_for_extraction'] == 'yes')
    print(f'Surveyed {len(rows)} documents -> {OUT_SURVEY}')
    print(f'  has_table=yes: {n_table}')
    print(f'  has_table=unknown (picture page): {n_unknown}')
    print(f'  already_captured_by non-empty: {n_captured}')
    print(f'  candidate_for_extraction=yes: {n_candidate}')
    print(f'Extracted {len(EXTRACTED_TABLES)} table cells from 7 documents -> {OUT_TABLES}')
