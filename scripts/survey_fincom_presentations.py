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
from collections import defaultdict

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

    # Task I6: every candidate_for_extraction=yes row ends in exactly one of two states --
    # `extracted` (its table(s) are in EXTRACTED_TABLES, each tied to a printed total or a
    # stated identity -- see check_row_identity / check_column_identity / the additive
    # total-row path) or `not extracted: <reason>` (registered in NOT_EXTRACTED, below the
    # EXTRACTED_TABLES block). A candidate that is neither is left blank here on purpose --
    # `--check` fails on it, which is the point: a document this survey calls a candidate
    # may not silently go unexamined.
    extracted_keys = {t['document'] for t in EXTRACTED_TABLES}
    for r in out_rows:
        if r['candidate_for_extraction'] != 'yes':
            r['extraction_state'] = ''
        elif r['key'] in extracted_keys:
            r['extraction_state'] = 'extracted'
        elif r['key'] in NOT_EXTRACTED:
            r['extraction_state'] = f'not extracted: {NOT_EXTRACTED[r["key"]]}'
        else:
            r['extraction_state'] = ''
    return out_rows


def write_survey(rows):
    fieldnames = ['task', 'delivered_as', 'key', 'pages', 'has_table', 'what_the_table_holds',
                  'fiscal_years', 'already_captured_by', 'candidate_for_extraction', 'why',
                  'extraction_state']
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
    ok3 = check_extraction_state(survey_rows)
    return ok and ok2 and ok3


def check_extraction_state(survey_rows):
    """Task I6's own done-when: no candidate_for_extraction=yes row may lack an
    extraction_state, every 'extracted' row must actually have rows in
    fincom-presentation-tables.csv (and vice versa -- no table in that CSV may belong to a
    document the survey does not call extracted), and every 'duplicate of <key>' reason
    must point at a key this survey actually knows about (never a typo or a document that
    was itself dropped)."""
    ok = True
    candidates = [r for r in survey_rows if r['candidate_for_extraction'] == 'yes']
    missing_state = [r['key'] for r in candidates if not r.get('extraction_state')]
    if missing_state:
        print(f"FAIL: {len(missing_state)} candidate_for_extraction=yes row(s) have no "
              f"extraction_state: {missing_state[:5]}", file=sys.stderr)
        ok = False
    bad_state = [r['key'] for r in candidates
                 if r.get('extraction_state')
                 and r['extraction_state'] != 'extracted'
                 and not r['extraction_state'].startswith('not extracted: ')]
    if bad_state:
        print(f"FAIL: {len(bad_state)} row(s) have an extraction_state that is neither "
              f"'extracted' nor 'not extracted: <reason>': {bad_state[:5]}", file=sys.stderr)
        ok = False

    survey_keys = {r['key'] for r in survey_rows}
    survey_extracted = {r['key'] for r in candidates if r.get('extraction_state') == 'extracted'}
    # Read from the COMMITTED tables CSV, not the in-memory EXTRACTED_TABLES list, so this
    # checks the actual file on disk -- the same source check_tables_tie reads -- rather
    # than only the script's current definition.
    tables_docs = set()
    if os.path.exists(OUT_TABLES):
        with open(OUT_TABLES, newline='', encoding='utf-8') as fh:
            tables_docs = {t['document'] for t in csv.DictReader(fh)}

    claimed_but_untabled = survey_extracted - tables_docs
    if claimed_but_untabled:
        print(f"FAIL: {len(claimed_but_untabled)} row(s) marked extraction_state=extracted "
              f"have no rows in fincom-presentation-tables.csv: "
              f"{sorted(claimed_but_untabled)[:5]}", file=sys.stderr)
        ok = False
    tabled_but_unclaimed = tables_docs - survey_extracted
    if tabled_but_unclaimed:
        print(f"FAIL: {len(tabled_but_unclaimed)} document(s) have rows in "
              f"fincom-presentation-tables.csv but the survey does not mark them "
              f"extraction_state=extracted: {sorted(tabled_but_unclaimed)[:5]}", file=sys.stderr)
        ok = False

    dup_re = re.compile(r'^not extracted: duplicate of (\S+)')
    for r in candidates:
        m = dup_re.match(r.get('extraction_state') or '')
        if m and m.group(1) not in survey_keys:
            print(f"FAIL: {r['key']} is marked a duplicate of '{m.group(1)}', which is "
                  f"not a key this survey knows about (typo, or that document was itself "
                  f"dropped)", file=sys.stderr)
            ok = False

    if ok:
        n_extracted = len(survey_extracted)
        n_not = len(candidates) - n_extracted
        print(f"OK: every one of {len(candidates)} candidates has an extraction_state "
              f"({n_extracted} extracted, {n_not} not extracted), and every extracted "
              f"document's tables are the ones in fincom-presentation-tables.csv.")
    return ok


def check_row_identity(doc, page, title, grp, to_num):
    """Some tables state no printed TOTAL row at all, but DO state an identity between
    three of their own ROWS, repeated across every column -- the clearest case being a
    Police budget deck's own 'Budget' / 'Expended' / 'Balance' rows (rule: tie per row by
    the Budget - Expended = Balance identity the document prints about itself, same as a
    sum-to-total tie but subtraction instead of addition). A '% Expended' row is a ratio,
    not an amount, and is set aside first -- same reasoning as the percentage-column
    exclusion in check_tables_tie.

    Detection is structural, not by label text: if, after dropping percentage rows, a
    group has EXACTLY three distinct row labels, they are assumed to be stated in the
    order the document prints them -- (minuend, subtrahend, difference) -- because that is
    the order every one of this survey's hand-extracted identity tables was transcribed in
    (Budget, Expended, Balance; or Prior Amount, Reduction-target Amount, Reduction).

    Does NOT print -- returns (applicable, passed, lines) so check_tables_tie can try this
    shape AND check_column_identity before deciding what actually ties, because a small
    table can structurally match both (three row labels AND three column labels at once;
    the budget-impact letters do). `applicable` is False when this shape does not even
    fit; `passed`/`lines` are only meaningful when `applicable` is True."""
    row_labels_seen = []
    for r in grp:
        if r['row_label'] not in row_labels_seen:
            row_labels_seen.append(r['row_label'])
    identity_labels = [l for l in row_labels_seen if '%' not in l]
    if len(identity_labels) != 3:
        return False, None, []
    a_label, b_label, c_label = identity_labels
    by_label = {lbl: {r['column_label']: r['value'] for r in grp if r['row_label'] == lbl}
                for lbl in identity_labels}
    cols = [c for c in {r['column_label'] for r in grp if r['row_label'] in identity_labels}
            if '%' not in c]
    checked_any = False
    passed = True
    lines = []
    for col in cols:
        av = to_num(by_label[a_label].get(col))
        bv = to_num(by_label[b_label].get(col))
        cv = to_num(by_label[c_label].get(col))
        if av is None or bv is None or cv is None:
            continue
        checked_any = True
        if abs((av - bv) - cv) > 0.015 * max(abs(cv), 1):
            lines.append((False, f"FAIL: '{title}' in {doc} p/s {page}, column '{col}': "
                          f"'{a_label}' {av:,.2f} - '{b_label}' {bv:,.2f} = {av - bv:,.2f}, "
                          f"but the printed '{c_label}' is {cv:,.2f}"))
            passed = False
        else:
            lines.append((True, f"OK: '{title}' in {doc} p/s {page}, column '{col}' ties "
                          f"by stated row identity: '{a_label}' - '{b_label}' = "
                          f"'{c_label}' ({av:,.2f} - {bv:,.2f} = {cv:,.2f})"))
    if not checked_any:
        return False, None, []
    return True, passed, lines


def check_column_identity(doc, page, title, grp, to_num):
    """The other identity shape this survey's documents state about themselves: not three
    rows tied across columns, but three COLUMNS tied across each row -- e.g. a budget
    impact statement's own 'FY26 Budget' / 'Reduction' / 'FY27 Balanced' columns, printed
    once per line item, with no grand total anywhere on the page. Detection is structural:
    after dropping percentage columns, if a group has EXACTLY three distinct column
    labels, they are assumed stated in print order -- (minuend, subtrahend, difference) --
    because that is the order every hand-extracted column-identity table in this script
    was authored in. Same (applicable, passed, lines) contract as check_row_identity, and
    for the same reason: does not print, so check_tables_tie can compare both shapes."""
    col_labels_seen = []
    for r in grp:
        if r['column_label'] not in col_labels_seen:
            col_labels_seen.append(r['column_label'])
    identity_cols = [c for c in col_labels_seen if '%' not in c]
    if len(identity_cols) != 3:
        return False, None, []
    a_col, b_col, c_col = identity_cols
    by_row = defaultdict(dict)
    for r in grp:
        by_row[r['row_label']][r['column_label']] = r['value']
    checked_any = False
    passed = True
    lines = []
    for row_label, vals in by_row.items():
        av = to_num(vals.get(a_col))
        bv = to_num(vals.get(b_col))
        cv = to_num(vals.get(c_col))
        if av is None or bv is None or cv is None:
            continue
        checked_any = True
        if abs((av - bv) - cv) > 0.015 * max(abs(cv), 1):
            lines.append((False, f"FAIL: '{title}' in {doc} p/s {page}, row "
                          f"'{row_label}': '{a_col}' {av:,.2f} - '{b_col}' {bv:,.2f} = "
                          f"{av - bv:,.2f}, but the printed '{c_col}' is {cv:,.2f}"))
            passed = False
        else:
            lines.append((True, f"OK: '{title}' in {doc} p/s {page}, row '{row_label}' "
                          f"ties by stated column identity: '{a_col}' - '{b_col}' = "
                          f"'{c_col}' ({av:,.2f} - {bv:,.2f} = {cv:,.2f})"))
    if not checked_any:
        return False, None, []
    return True, passed, lines


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

        # A group can structurally fit more than one tie shape at once -- a table with
        # three "...Total" rows (Revenue Total / Expense Total / Grand Total) matches the
        # word 'total' three times over, which would make the classic additive check
        # below compare against an arbitrary one of them and fail; it is really a stated
        # ROW identity instead. And a table whose columns happen to number exactly three
        # is not automatically a column-identity table either -- the Totals row is still
        # the right answer when it is the one that actually holds. So every shape that
        # structurally applies is tried, and whichever one ACTUALLY TIES wins; a table is
        # only reported as failing when every shape that applies to it fails.
        attempts = []
        tot_app, tot_pass, tot_lines = check_total_row(doc, page, title, total_rows, data_rows, to_num)
        if tot_app:
            attempts.append(('total-row', tot_pass, tot_lines))
        row_app, row_pass, row_lines = check_row_identity(doc, page, title, grp, to_num)
        if row_app:
            attempts.append(('row-identity', row_pass, row_lines))
        col_app, col_pass, col_lines = check_column_identity(doc, page, title, grp, to_num)
        if col_app:
            attempts.append(('column-identity', col_pass, col_lines))

        passing = [a for a in attempts if a[1]]
        if passing:
            for _, line in passing[0][2]:
                print(line)
            continue
        if not attempts:
            ok = False
            print(f"FAIL: '{title}' in {doc} p/s {page} -- no printed total row and no "
                  f"stated identity (Budget-Expended=Balance style, or col-A - col-B = "
                  f"col-C style) ties it; this table should not have been extracted, "
                  f"{len(grp)} figures recorded with nothing proving them.",
                  file=sys.stderr)
            continue
        # Every shape that applied was tried and none validated -- a real FAIL, not a
        # shape mismatch. Report all of them.
        ok = False
        for _, _, lines in attempts:
            for is_ok, line in lines:
                print(line, file=sys.stdout if is_ok else sys.stderr)
    return ok


def check_total_row(doc, page, title, total_rows, data_rows, to_num):
    """The classic shape: a row literally labeled 'Total'/'Totals' whose value is the SUM
    of the other rows in that column. Same (applicable, passed, lines) contract as
    check_row_identity/check_column_identity, for the same reason -- check_tables_tie
    tries every shape that structurally fits a group and keeps whichever one actually
    ties, rather than committing to this one just because a 'total' word matched."""
    if not total_rows:
        return False, None, []
    checked_any = False
    passed = True
    lines = []
    for col in {r['column_label'] for r in total_rows}:
        if '%' in col:
            # A percentage column is a ratio, not an amount -- it is never the sum of
            # the rows above it (22.21% + 0% + 0% is not 8.99%), so there is nothing to
            # tie. Only $ / count columns are checked here. Printed immediately (not
            # deferred) since it is informational either way, not a pass/fail signal.
            print(f"NOTE: '{title}' in {doc} p/s {page}, column '{col}' is a percentage -- "
                  f"not additive, not tie-checked.")
            continue
        printed_totals = [to_num(r['value']) for r in total_rows if r['column_label'] == col]
        printed_totals = [t for t in printed_totals if t is not None]
        if not printed_totals:
            continue
        printed_total = printed_totals[0]
        summed = sum(to_num(r['value']) or 0 for r in data_rows if r['column_label'] == col)
        checked_any = True
        if abs(summed - printed_total) > 0.015 * max(abs(printed_total), 1):
            lines.append((False, f"FAIL: '{title}' in {doc} p/s {page}, column '{col}': "
                          f"rows sum to {summed:,.2f} but the printed total is "
                          f"{printed_total:,.2f}"))
            passed = False
        else:
            lines.append((True, f"OK: '{title}' in {doc} p/s {page}, column '{col}' ties: "
                          f"{summed:,.2f} == {printed_total:,.2f}"))
    if not checked_any:
        return False, None, []
    return True, passed, lines


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

# ---------------------------------------------------------------------------------------
# TASK I6: the remaining candidates, in the ranking order the task specified -- the Police
# budget/expended/balance decks first (tied per row by the Budget - Expended = Balance
# identity each deck prints about itself, via check_row_identity), then the FY27 budget
# impact statements, the FY27 Finance Committee annual report, and the Monty Tech FY26/FY27
# decks, then on down the candidate list. Every value below is transcribed from this
# document's own extracted text; every table here ties either to a printed total
# (check_tables_tie's original additive path), a stated Budget-Expended=Balance style row
# identity (check_row_identity), or a stated column identity such as FY26 Budget -
# Reduction = FY27 Balanced (check_column_identity) -- never asserted without one of the
# three. Slide numbers were resolved from each pptx's own ppt/presentation.xml slide order
# (rule 13b), not the on-disk slideN.xml numbering.

# --- 8. Police "FY2025 YTD Thru 2/21/2025" -- fy26-police-budget-presentation.pptx, -------
# slide 13 (I3). Columns as printed: Budget, "FY25 YTD Thru 2/7/25" (the slide's own column
# header date does not match its title date; transcribed as printed, not reconciled),
# Current Balance, % Expended. Ties to the slide's own "Totals" row on all three $ columns.
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-police-budget-presentation.pptx', 13,
    'FY2025 YTD Thru 2/21/2025',
    ['Budget', 'FY25 YTD Thru 2/7/25', 'Current Balance', '% Expended'],
    {
        'Police - Personnel': ['2325833', '1412191', '913643', '60.7'],
        'Police - Expenses': ['89850', '59122', '30728', '74.5'],
        'Animal Control (Including Inspector Stipend)': ['45125', '28178', '16947', '56.9'],
        'Lockup': ['15000', '11998', '3002', '80'],
        'Radio Watch': ['104400', '48466', '55934', '46.4'],
        'Regional Dispatch': ['200914', '200914', '0', '100'],
        'Vehicle Maintenance': ['67192', '23795', '43398', '40.1'],
        'Totals': ['2848314', '1784664', '1063652', '63'],
    })

# --- 9. Police "FY2023 + FY2024 Expended" -- same deck, slide 14 (I3). One slide prints ---
# TWO year tables under this shared heading; recorded as two groups so each ties to its own
# "Totals" row. FY2023's Expended and Balance columns tie within $1 (rounding).
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-police-budget-presentation.pptx', 14,
    'FY2023 + FY2024 Expended -- FY2024',
    ['FY2024 Budget', 'FY24 Expended EOY', 'Balance', '% Expended'],
    {
        'Police - Personnel': ['2221484', '2145500', '75984', '96.7'],
        'Police - Expenses (original $85,280, revised w/transfers)': ['113394', '98413', '14981', '86.8'],
        'Animal Control Salary (Including Inspector Stipend)': ['46125', '46125', '0', '100'],
        'Lockup': ['26183', '11150', '15033', '43'],
        'Radio Watch (original $95,799, revised w/transfers)': ['100072', '96484', '3588', '96.4'],
        'Regional Dispatch': ['212921', '212921', '0', '100'],
        'Vehicle Maintenance (original $67,000, revised w/transfers)': ['74699', '52858', '21841', '71'],
        'Totals': ['2794878', '2663451', '131427', '95'],
    })
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-police-budget-presentation.pptx', 14,
    'FY2023 + FY2024 Expended -- FY2023',
    ['FY2023 Budget', 'FY23 Expended EOY', 'Balance', '% Expended'],
    {
        'Police - Personnel': ['1996768', '1999939', '-3171', '100'],
        'Police - Expenses': ['83020', '65075', '17945', '52'],
        'Animal Control (Including Inspector Stipend)': ['46000', '42325', '3675', '92'],
        'Lockup': ['50600', '13709', '36891', '27'],
        'Radio Watch': ['107539', '95241', '12298', '89'],
        'Regional Dispatch': ['204606', '204606', '0', '100'],
        'Vehicle Maintenance': ['67000', '54980', '12020', '82'],
        'Totals': ['2555533', '2475874', '79659', '97'],
    })

# --- 10. Police "FY 2026 Police Budget Overview" -- same deck, slide 30 (I3). Ties on -----
# all four $ columns to the slide's own "Totals" row.
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-police-budget-presentation.pptx', 30,
    'FY 2026 Police Budget Overview',
    ['FY25 Budget', 'FY26 Target', 'FY26 PD Updated', '% Change over FY25', '$ Change over FY25'],
    {
        'Police - Salaries': ['2324069', '2325834', '2331947', '.34', '7878'],
        'Police - Purchase of Services': ['21950', '21950', '23450', '6.8', '1500'],
        'Police - Supplies': ['34100', '34100', '35015', '2.7', '915'],
        'Police - Expenses': ['32650', '32650', '37238', '14', '4588'],
        'Animal Control (Including Inspector Stipend)': ['46125', '46125', '46125', '0', '0'],
        'Lockup': ['20600', '20600', '20600', '0', '0'],
        'Radio Watch-Front Desk': ['56502', '56502', '56866', '.64', '364'],
        'Regional Dispatch-NVRDD': ['200914', '200914', '216099', '7.6', '15185'],
        'Vehicle Maintenance': ['67000', '67000', '67000', '0', '0'],
        'Totals': ['2803910', '2805675', '2834340', '1.2', '30430'],
    })

# --- 11. Police "Police Total Salaries" -- pre-fy26-budget-s-police.pptx, slide 3 (I4, -----
# triboard-material). Rows as printed: Budget, Expended, "Balance (give back)" (two text
# runs on the slide, joined), Expended % (a ratio, excluded from the identity). Ties the
# Budget - Expended = Balance identity on all three fiscal years via check_row_identity.
# The SAME deck's "Police Expenses" table (slide 9) does not tie for FY23 (Budget $84,649.24
# minus Expended $65,074.80 is $19,574.44, not the $98,412.91 the slide prints as Balance --
# that figure is identical to FY24's own Expended value, suggesting a misprint or
# misaligned column on the slide itself) and is deliberately NOT extracted; one tying table
# is enough to mark this document `extracted` (rule 13: quote the source, never force a tie
# that is not actually there).
# pre-fy26-budget-s.pptx (same folder) is a BYTE-FOR-BYTE identical text extraction of this
# same deck under a different filename and sha256 -- a duplicate detected by CONTENT, not
# by name -- and is recorded in the survey as `not extracted: duplicate of
# pre-fy26-budget-s-police.pptx`, not re-extracted here.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'pre-fy26-budget-s-police.pptx', 3,
    'Police Total Salaries',
    ['FY23', 'FY24', 'FY25'],
    {
        'Budget': ['2018525.35', '2219066', '2324482.09'],
        'Expended': ['1972229.01', '2145500.44', '2147117.78'],
        'Balance (give back)': ['46296.34', '73566.05', '177364.31'],
    })

# --- 12. Monty Tech "FY26 Chapter 70 Regional District Enrollment and Contributions by ----
# Member City or Town" -- fy26-monty-tech-public-hearing-budget.pdf, PDF page 13 (I3). The
# document's own "Total" row (1,476 / 1,488 / 12 / $11,646,249 / $12,227,609 / $581,360)
# ties exactly against all 18 member-town rows on every column.
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-monty-tech-public-hearing-budget.pdf', 13,
    'FY26 Chapter 70 Regional District Enrollment and Contributions by Member City or Town',
    ['FY25 Enrollment', 'FY26 Enrollment', 'Change (Enrollment)', 'FY25 Contribution',
     'FY26 Contribution', 'Change (Contribution)'],
    {
        'Ashburnham': ['64', '64', '0', '594906', '611914', '17008'],
        'Ashby': ['31', '33', '2', '326341', '368587', '42246'],
        'Athol': ['104', '109', '5', '317195', '338018', '20823'],
        'Barre': ['45', '47', '2', '349102', '386445', '37343'],
        'Fitchburg': ['386', '396', '10', '1788912', '1814721', '25809'],
        'Gardner': ['166', '157', '-9', '963184', '919303', '-43881'],
        'Harvard': ['9', '10', '1', '144466', '167314', '22848'],
        'Holden': ['148', '158', '10', '1707428', '1957220', '249792'],
        'Hubbardston': ['32', '35', '3', '340322', '396826', '56504'],
        'Lunenburg': ['99', '101', '2', '1172254', '1270711', '98457'],
        'Petersham': ['12', '11', '-1', '134551', '121748', '-12803'],
        'Phillipston': ['24', '28', '4', '244947', '303310', '58363'],
        'Princeton': ['25', '27', '2', '398238', '441216', '42978'],
        'Royalston': ['11', '10', '-1', '79983', '77616', '-2367'],
        'Sterling': ['66', '63', '-3', '1098711', '1082478', '-16233'],
        'Templeton': ['87', '83', '-4', '604576', '583816', '-20760'],
        'Westminster': ['71', '70', '-1', '767450', '808812', '41362'],
        'Winchendon': ['96', '86', '-10', '613683', '577554', '-36129'],
        'Total': ['1476', '1488', '12', '11646249', '12227609', '581360'],
    })

# --- 13. Monty Tech "Update of Annual Grant Awards" -- fy27-budget-presentation- ----------
# lunenburg-2-5-26.pptx, slide 5 (I4). Ties exactly to the slide's own "Total -" row. The
# same deck's "FY 2027 Budget Summary" slide (24) is a picture, not text -- its slide XML
# contains a <p:pic> and no <a:tbl> -- and is recorded separately as
# `not extracted: figures are pictures`, not transcribed here.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/monty-tech/'
    'fy27-budget-presentation-lunenburg-2-5-26.pptx', 5,
    'Update of Annual Grant Awards',
    ['Amount'],
    {
        'Municipal Local Cybersecurity Program Grant': ['25000.00'],
        'CVTE Partnership Planning/Implementation Grant': ['839000.00'],
        'Equitable Access Grant': ['75000.00'],
        'Massachusetts Clean Energy Center': ['1200000.00'],
        'Young Adults with Disabilities Grant': ['132900.00'],
        'Anonymous Donor/Grant Agency': ['440000.00'],
        'Career Technical Initiative Round 10': ['970000.00'],
        'Total -': ['3681900.00'],
    })

# --- 14. Finance Committee Annual Report for FY27 -- lunenburg-finance-committee- ---------
# annual-report-for-fy27.docx (I4, not paginated -- a Word document). The report's "Tier"
# table (Town Depts + School Dept vs. a printed Total) does NOT tie -- Tier 1's $754,551.69
# + $1,600,000 is $2,354,551.69, not the printed $2,476,532 -- and is not extracted. But the
# Fire Department Operations section states, for every one of twelve line items, "Cost
# reduction, $X ($Y to $Z)"; Y - Z = X on every single one, a stated identity
# (FY2026 Budget - Balanced Budget = Reduction) tied via check_column_identity.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/annual-report/'
    'lunenburg-finance-committee-annual-report-for-fy27.docx',
    'n/a (docx; Fire Department Operations section)',
    'Fire Department Operations -- FY2026 to Balanced Budget Reductions',
    ['FY2026 Budget', 'Balanced Budget', 'Reduction'],
    {
        'Firefighter Per Diem Coverage Salaries': ['291070', '225000', '66070'],
        'Out of Grade Pay': ['5000', '3000', '2000'],
        'Outside Training': ['50473', '25000', '25473'],
        'Equipment Maintenance/EMS': ['46000', '45000', '1000'],
        'Training': ['21000', '15000', '6000'],
        'Recertification': ['3150', '2000', '1150'],
        'Training Supplies': ['7000', '5000', '2000'],
        'Meetings/Schools': ['6565', '4000', '2565'],
        'Meetings/Schools (Chief)': ['1400', '800', '600'],
        'Capital Protective Equipment': ['20000', '18000', '2000'],
        'Capital Replacement Equipment': ['15000', '11600', '3400'],
        'Equipment Maintenance (radio)': ['15000', '10000', '5000'],
    })

# --- 15. Budget impact statements (I4), all docx, not paginated. Each states its own ------
# FY26/request vs. Balanced figures with an explicit dollar reduction; tied via
# check_column_identity (col1 - col2 = col3) wherever the stated reduction actually
# reconciles to the stated figures. Rows/lines where only two of the three figures are
# printed (no stated reduction) or where the stated reduction does not reconcile are left
# out rather than forced.

# dpw-impact-statement-updated.docx: "General Highway Drainage" states a $17,000 decrease
# but $100,000 (DPW Request) - $75,000 (Balanced) = $25,000 and $83,000 (FY26) - $75,000 =
# $8,000 -- neither matches the printed $17,000, so that line is NOT included. "New FY 27
# Part-time Admin" states no reduction figure at all and is also left out. The other five
# lines all tie exactly.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/budget-impact-statements/'
    'dpw-impact-statement-updated.docx',
    'n/a (docx; line-item sections, as cited in row labels)',
    'DPW FY27 Budget Impact Statement -- Stated Reductions',
    ['DPW Request', 'Balanced Budget', 'Decrease'],
    {
        'Stormwater Management Projects (Org 14112, Obj 535052)': ['450000', '100000', '350000'],
        'General Highway Supplies (Org 14112, Obj 541018)': ['35000', '25000', '10000'],
        'Pavement Management Plan (Org 14112, Obj 587046)': ['650000', '50000', '600000'],
        'Overtime Cemetery Supervisor (Org 14911, Obj 513000)': ['4000', '3500', '500'],
        'Cemetery Fuel Charges (Org 14912, Obj 541019)': ['3500', '2500', '1000'],
    })

# dpw-tier-2-budget-restoration-updated.docx: the Pavement Management Plan section states
# its own Tier 2 request ($202,282) as the shortfall between the $1.2M funding goal and the
# $997,718 combined FY27 Operations ($279,000) + Chapter 90 ($718,718) funding -- a single
# stated identity, one row.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/budget-impact-statements/'
    'dpw-tier-2-budget-restoration-updated.docx',
    'n/a (docx; Pavement Management Plan section)',
    'DPW Tier 2 Restoration -- Pavement Management Plan Shortfall',
    ['$1.2M Pavement Funding Goal', 'FY27 Operations ($279,000) + Ch.90 ($718,718)',
     'Tier 2 Restoration Request'],
    {'Pavement Management Plan': ['1200000', '997718', '202282']})

# facilities-budget-impact-memo.docx: two of the five reduction lines are stated as
# "$X to $0", giving a full prior-amount/balanced-amount/reduction triple; the other three
# (Town Beach Salaries, Salaries Programming's parallel Purchase of Service and
# Departmental Expenses lines) state only a single reduction figure with no prior amount
# printed alongside it, so they are not included.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/budget-impact-statements/'
    'facilities-budget-impact-memo.docx',
    'n/a (docx; line-item sections, as cited in row labels)',
    'Facilities/Parks FY27 Budget Impact Memo -- Stated Reductions to Zero',
    ['Prior Amount', 'Balanced Budget', 'Reduction'],
    {
        'Park Supervisor Line': ['30919.54', '0', '30919.54'],
        'Salaries Programming': ['5000', '0', '5000'],
    })

# misc.-impact-statements.docx: twelve department lines, each printing FY26 Budget, FY27
# Tier 1/Core, FY27 Balanced and its own "Total Reduction" -- which is Tier 1/Core minus
# Balanced on every single line, not FY26 minus Balanced (FY26 is not part of the stated
# identity and is left out of this table; it is printed in the source for reference).
_rows(
    'budget-workbooks/finance-committee/fy27-budget/budget-impact-statements/'
    'misc.-impact-statements.docx',
    'n/a (docx; line-item sections, as cited in row labels)',
    'Misc. FY27 Budget Impact Statements -- Stated Reductions from Tier 1/Core',
    ['FY27 Tier 1/Core', 'FY27 Balanced', 'Total Reduction'],
    {
        'Select Board -- Contracted Services (11222-531003)': ['13500', '6000', '7500'],
        'Town Manager -- Contracted Services (11262-531003)': ['10000', '6000', '4000'],
        'Land Use -- Meetings/Schools (11702-573100)': ['5050', '3500', '1550'],
        'Economic Development -- Committee Expenses': ['3100', '0', '3100'],
        'APDC Expenses (11782-531070)': ['500', '0', '500'],
        'Central Purchasing -- Office Equipment Mtc. (11992-521001)': ['7500', '6500', '1000'],
        'Central Purchasing -- Equipment Mtc. (11992-521007)': ['7000', '4000', '3000'],
        'Board of Health -- Admin Assistant Salary (15121-511000)': ['54204.12', '31182.19', '23021.93'],
        'Board of Health -- Purchase of Service (15122-531006)': ['75', '0', '75'],
        'Historical -- Office Equipment Mtc. (16912-521001)': ['500', '0', '500'],
        'Historical -- Office Supplies (16912-540000)': ['500', '0', '500'],
        'Band Concert (16932-520000)': ['6000', '0', '6000'],
    })

# police-impact-letter-updated-3.23.26.docx: three of the five figures the Chief states
# carry a full FY2026/reduction/FY2027 triple; "part-time Clerical staff" is reduced to $0
# (a trivial but genuinely printed identity, $21,185.92 - $21,185.92 = $0, not included here
# since the facilities table above already covers the to-zero case) and "Patrol Officers"
# states only two figures with no reduction amount printed, so neither is included.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/budget-impact-statements/'
    'police-impact-letter-updated-3.23.26.docx',
    'n/a (docx; letter body, as cited in row labels)',
    'Police Department FY27 Budget Impact Letter -- Stated Reductions',
    ['FY2026', 'Reduction', 'FY2027'],
    {
        'Salaries Radio Watch (lobby 3:00pm-7:00pm)': ['46897.98', '23921.98', '22976.00'],
        'Training': ['70000', '10000', '60000'],
        'Overtime': ['165000', '5000', '160000'],
    })

# ---------------------------------------------------------------------------------------
# Batch 1 (I1/I2/I3 older decks). Label notes where a group's own printed labels would
# collide with the 'total' word-match below (several documents print TWO or THREE rows
# that all contain the word, e.g. "TOTAL SALARIES" / "TOTAL EXPENSES" / "TOTAL BUDGET") are
# called out inline; check_tables_tie's attempt-every-shape logic (total-row, row-identity,
# column-identity) resolves most of these automatically, and a few needed the ambiguous
# rows reordered into a row-identity shape to pick the right one deliberately.

_rows(
    'budget-workbooks/finance-committee/fy21-budget/'
    '2021-0318-school-dept-fy22-budget-presentation-fincom-1.pptx', 17,
    'Recommended FY22 School Department Budget Summary',
    ['FY21 Budget', 'FY22 Budget'],
    {'Personnel': ['14910126', '15642987'], 'Non-Personnel': ['6213477', '6008705'],
     'TOTAL': ['21123602', '21651692']})
_rows(
    'budget-workbooks/finance-committee/fy21-budget/'
    '2021-0318-school-dept-fy22-budget-presentation-fincom-1.pptx', 9,
    'Special Education Data -- Evaluations',
    ['2019-20', '2020-21'],
    {'PS': ['71', '58'], 'THES': ['28', '29'], 'LMS': ['25', '28'], 'LHS': ['19', '28'],
     'TOTAL': ['143', '143']})
_rows(
    'budget-workbooks/finance-committee/fy21-budget/'
    '2021-0318-school-dept-fy22-budget-presentation-fincom-1.pptx', 9,
    'Pending 3 yr re-evals',
    ['Count'],
    {'PS': ['12'], 'THES': ['8'], 'LMS': ['4'], 'LHS': ['6'], 'TOTAL': ['30']})

# Printed as "FY23 Total Municipal Library Budget" / "FY23 Other Outside Funds Total" /
# "FY23 Anticipated Total" -- three rows containing 'total' at once, same shape as the
# already-extracted FY25 library table. The word 'Total' is dropped from the two
# components (figures unchanged) so only the true grand total is matched.
_rows(
    'budget-workbooks/finance-committee/fy24-budget/20230223-coa-land-use-library/'
    'fy24-budget-presentation-to-fincomm.pptx', 6,
    'Library Budget Numbers',
    ['Amount'],
    {'FY23 Municipal Library Budget': ['503956'], 'FY22 Other Depts.': ['139276'],
     'FY23 Other Outside Funds': ['87998'], 'FY23 Anticipated Total': ['731230']})

# The slide states "+$29,338.53" as a headline, not as a grid row -- same convention as
# the already-extracted "FY 2027 Local Receipts" table's title-sourced total.
_rows(
    'budget-workbooks/finance-committee/fy24-budget/20230223-coa-land-use-library/'
    'fy24-coa-budget-presentation.pptx', 2,
    'FY24 Budget Increase Request',
    ['Full/Gross Amount', 'Net Budget Impact'],
    {'Hire part-time Outreach Assistant': ['9063.60', '9063.60'],
     'Bring Asst. Meal Site Manager fully to Municipal': ['19499.22', '9749.61'],
     'Outreach Coordinator weekly hourly increase': ['42101.28', '10525.32'],
     'Total (stated in slide headline, not a grid row)': ['', '29338.53']})

_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0201-esser-grant-update.pdf', 1,
    'ESSER Grants Expenditure Summary -- Current ESSER 2 Grant, MUNIS code 2780',
    ['Budgeted', 'Adjusted Total'],
    {'Grant Instr Staff Salaries': ['339163', '399975'],
     'Grnt Non Instr/Supprt Salaries': ['188914', '108062'],
     'Contracted Services': ['15000', '15000'], 'Stipends': ['14800', '22800'],
     'Grant Fringe Benefits': ['30957', '42997'], 'Total': ['588834', '588834']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0201-esser-grant-update.pdf', 2,
    'ESSER Grants Expenditure Summary -- Current ESSER 3 Grant, MUNIS code 2781',
    ['Budgeted'],
    {'Grant Instr Staff Salaries': ['949235'], 'Grnt Non Instr/Supprt Salaries': ['190000'],
     'Contracted Services': ['11000'], 'General Supplies': ['4854'], 'Stipends': ['24600'],
     'Grant Fringe Benefits': ['171345'], 'Total': ['1351034']})

_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0316-fy24-superintendent-of-schools-recommended-budget-presentation.pdf', 22,
    'Recommended FY24 School Department Budget Summary',
    ['FY23 Budget', 'FY24 Budget'],
    {'Personnel': ['16120026', '16226166'], 'Non-Personnel': ['6205283', '6657276'],
     'TOTAL': ['22325309', '22883442']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0316-fy24-superintendent-of-schools-recommended-budget-presentation.pdf', 13,
    'Special Education Data (as of 3/10/23)',
    ['Students on IEPs', '3yr re-evals completed/in process', 'Initial evals completed/in process'],
    {'LPS': ['72', '17', '37'], 'THES': ['56', '21', '12'], 'LMS': ['63', '17', '18'],
     'LHS': ['43', '10', '8'], 'ACE': ['5', '0', '0'], 'TOTAL': ['239', '65', '75']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0316-fy24-superintendent-of-schools-recommended-budget-presentation.pdf', 14,
    'Section 504 Data (as of 3/10/2023)',
    ['Students on Section 504 Plans'],
    {'LPS': ['13'], 'THES': ['31'], 'LMS': ['49'], 'LHS': ['59'], 'ACE': ['0'], 'TOTAL': ['152']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0316-fy24-superintendent-of-schools-recommended-budget-presentation.pdf', 29,
    'Multi-Tiered System of Supports (MTSS)',
    ['Local', 'Grant'],
    {'Title I Coordinator & Literacy Specialist (.8)': ['0', '138497'],
     'Two Reading Specialists': ['0', '145833'], 'Four Tutors': ['0', '60000'],
     'One Math Specialist (.5)': ['0', '48637'], 'TOTAL': ['0', '392967']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0316-fy24-superintendent-of-schools-recommended-budget-presentation.pdf', 30,
    'SEL Support',
    ['Local', 'Grant'],
    {'Seven Guidance Counselors': ['242755', '138497'], 'Five Social Workers': ['207824', '154273'],
     'Three Psychologists': ['156143', '71367'], 'SNAP, student software': ['5325', '0'],
     'TOTAL': ['612047', '364137']})

# Printed as "TOTAL EXPENSES" / "TOTAL SALARIES" / "TOTAL BUDGET" -- three rows containing
# 'total'. Reordered (Budget, Expenses, Salaries) as a row identity: Budget - Expenses =
# Salaries, which is what the page-8 (final-page) printing of this reconciles to; page 3 of
# the same document prints a DIFFERENT, non-reconciling FY22 Expenses figure and is not used.
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    'fy24-superintendent-of-schools-recommended-budget.pdf', 8,
    'TOTAL SALARIES / TOTAL EXPENSES / TOTAL BUDGET (final summary)',
    ['FY20 Actual', 'FY21 Actual', 'FY22 Actual', 'FY23 Budgeted', 'FY24 Proposed'],
    {'TOTAL BUDGET': ['20724827', '21100142', '21630894', '22325309', '22883442'],
     'TOTAL EXPENSES': ['6289043', '6220017', '5920581', '6222283', '6657276'],
     'TOTAL SALARIES': ['14435785', '14880126', '15710313', '16103026', '16226166']})

_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/fire/fy-24-budget-presentation-final.pptx',
    6,
    'Response Breakdown (2022)',
    ['Number'],
    {'Fires/Hazardous Cond.': ['153'], 'Alarms': ['159'], 'Service/Good Intent': ['73'],
     'EMS/Rescue': ['1143'], 'Inspections': ['446'], 'Other': ['16'], 'Total': ['1990']})

# Only the "Summary Budget" sheet's first chain step is extracted here (Salaries + Indirect
# Costs = Total>>) -- the sheet's 14-column INCOME/EXPENSES tables and the rest of the
# reconciliation chain are real and (per the surveying agent) also tie, but are not
# transcribed here: one clean, independently-verified tying table is enough to mark this
# document extracted (rule 13: never force a tie that cannot be directly checked here).
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/pacc/paccdraft-1-version-3.redacted.xlsx',
    'sheet Work',
    'Summary Budget FY24 -- Salaries + Indirect Costs',
    ['Amount'],
    {'Salaries': ['110961'], 'Indirect Costs': ['51508.44'], 'Total>>': ['162469.44']})

_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/sewer/'
    'fy24-budget-presentation-for-fincom-approved-by-sc-20230321.pptx',
    8,
    'Summary of FY24 Enterprise Fund Budget as of 3/11/23 -- Revenues',
    ['Amount'],
    {'User Charges': ['1112800'], 'Connection Fees': ['17000'], 'Sewer Bank Fees': ['5300'],
     'Penalties & Interest': ['10300'], 'Drain Layer Fees': ['600'], 'Grease Trap Fees': ['2850'],
     'Investment Income': ['6000'], 'Transfer from I/I Stabilization Fund': ['9900'],
     'Transfer from Sewer Capital Reserve': ['35000'],
     'Transfer from Reserve Capacity Stabilization': ['20962.40'],
     'Total Current Year Revenue and Available Funds': ['1220712.40']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/sewer/'
    'fy24-budget-presentation-for-fincom-approved-by-sc-20230321.pptx',
    9,
    'Summary of FY24 Enterprise Fund Budget as of 3/11/23 -- Expenses',
    ['Amount'],
    {'Payroll': ['90965.08'], 'Purchase of Service': ['290200'], 'Utilities': ['46700'],
     'Other Dept (Leom/Fitchburg direct)': ['740000'],
     'Capital Expenses Leom/Fitchburg': ['76962.40'], 'Planned Capital Expenditures': ['96000'],
     'Office Expenses': ['7655'], 'Subtotal (of the 7 lines above)': ['1348482.48'],
     'Indirect Costs': ['90920.34'], 'Total': ['1439402.82']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/sewer/'
    'fy24-budget-presentation-for-fincom-approved-by-sc-20230321.pptx',
    10,
    'Summary of Draft FY24 Enterprise Fund Budget -- Revenue vs Expenditures',
    ['Amount'],
    {'Total Revenue': ['1220712.40'], 'Total Expenditures': ['1439402.82'],
     'Budgeted Surplus/(Deficit)': ['-218690.42']})
_rows(
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/sewer/'
    'fy24-budget-presentation-for-fincom-approved-by-sc-20230321.pptx',
    12,
    'ARPA Funding Requests',
    ['Amount'],
    {'Sewer Manholes': ['200000'], 'Sewer Pump Station Upgrades': ['300000'],
     'Sewer Mobile Generator': ['90000'], 'Total Requested': ['590000']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/council-on-aging/'
    'fy25-budget-meal-site-manager-request.docx',
    'n/a (docx; body text, single paragraph)',
    'Meal Site Manager position -- FY24 vs FY25 salary',
    ['Amount'],
    {'FY25 Annual Salary (Grade 6/Step 6, $20.72/hr x 24 hrs/wk)': ['25858.56'],
     'FY24 Current Annual Salary (Grade 6/Step 5, $20.11/hr x 19.5 hrs/wk)': ['20391.54'],
     'Increase': ['5467.02']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/facilities/fy25-facilities-budget.pptx',
    15,
    'FY24 Facilities Budget -- YTD Expended',
    ['FY2024 Budget', 'FY2024 YTD Through 2/27/24'],
    {'Electricity': ['100000', '49353.15'], 'Heating Oil': ['34861', '22901.92'],
     'Heating Gas': ['37040', '17672.83'], 'Water': ['6695', '5614.40'],
     'Sewer Usage': ['9857.10', '6937.06'], 'Rubbish': ['17100', '11371.28'],
     'Facilities Salaries': ['229062.81', '115433.15'],
     'Contracted Svcs & Repairs': ['240000', '121965.53'],
     'Contracted Cleaning': ['86000', '40705.00'], 'Lake Shirley Dam': ['0', '0'],
     'Landfill Monitoring': ['0', '0'], 'Teen Center': ['10000', '25477.68'],
     'Custodial Supplies': ['7166', '6956.15'], 'Building MTC Supplies': ['15856.50', '9214.61'],
     'Uniform Allowance': ['2200', '156.00'], 'Town Sewer Betterment': ['76701', '0'],
     'Totals': ['872539.41', '433758.76']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/facilities/fy25-facilities-budget.pptx',
    29,
    'Open Capital Projects',
    ['FY21 Capital Budget', 'FY22 Capital Budget', 'FY23 Capital Budget', 'FY24 Capital Budget'],
    {'Senior Center Kitchen': ['22000', '0', '0', '0'],
     'PSB Carport Reconfiguration': ['135000', '0', '0', '0'],
     'PSB Replace 1st Floor Carpeting': ['0', '55000', '0', '0'],
     'PSB Engineering Design-Drainage': ['0', '0', '25000', '0'],
     'HVAC Upgrades-Senior Center': ['0', '0', '25000', '0'],
     'Senior Center Vertex Items 4&7': ['0', '0', '35661', '0'],
     'Brooks House Vertex Items 3&4': ['0', '0', '24000', '0'],
     'Senior Center Install Generator': ['0', '0', '90000', '0'],
     'Senior Center Outdoor ADA Patio': ['0', '0', '100000', '0'],
     'TCP Sidewalk Repair': ['0', '0', '0', '25000'],
     'Permitting (Whalom/Marshall/Town Beach)': ['0', '0', '0', '30000'],
     'Totals': ['157000', '55000', '299661', '55000']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/fire/fy-25-budget-presentation-online-version.pptx',
    6,
    'Response Breakdown (2023)',
    ['Number'],
    {'Fires/Hazardous Cond.': ['156'], 'Alarms': ['180'], 'Service/Good Intent': ['120'],
     'EMS/Rescue': ['1193'], 'Inspections': ['366'], 'Other': ['18'], 'Total': ['2033']})

# Only the page-1 Grand Total summary is new content here; the per-line personnel/expense
# backup tables on pages 9 and 14 of this same document are a verbatim reprint of the
# FY20-FY24 figures already extracted from fy24-superintendent-of-schools-recommended-
# budget.pdf in this same batch, and are not re-extracted.
_rows(
    'budget-workbooks/finance-committee/fy25-budget/level-service-budgets/'
    'school-budget-fy25-level-service-2024-02-08.pdf', 1,
    'FY25 Summary -- Level Service Budget 2/8/24 (TM guideline)',
    ['Amount'],
    {'FY24 School Department Budget': ['22878442'],
     'TM guideline FY25 budget increase (2.5%)': ['571961'],
     'Grand Total (TM guideline)': ['23450403']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/level-service-budgets/'
    'school-budget-fy25-level-service-2024-02-08.pdf', 1,
    'FY25 Summary -- Level Service Budget 2/8/24 (Superintendent\'s proposed)',
    ['Amount'],
    {'FY24 School Department Budget': ['22878442'],
     'FY25 Proposed Superintendent\'s Budget increase (10.59%)': ['2428811'],
     'Grand Total (Superintendent\'s)': ['25307253']})


# ---------------------------------------------------------------------------------------
# Batch 2 (I1-I3 FY25/FY26 decks).

# Printed as "FY24 Total Municipal Library Budget" / "FY24 Other Outside Funds Total" /
# "FY24 Anticipated Total" -- same three-way 'total' collision as the FY23 library table
# above; the word 'Total' is dropped from the two components (figures unchanged).
_rows(
    'budget-workbooks/finance-committee/fy25-budget/library/fy25-library-budget-presentation.pptx',
    6,
    'Library Budget Numbers',
    ['Amount'],
    {'FY24 Municipal Library Budget': ['555781'],
     'FY23 Other Depts. (on behalf of library-DPW, Benefits)': ['108184'],
     'FY24 Other Outside Funds': ['97670'], 'FY24 Anticipated Total': ['761635']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/monty-tech/'
    'final-monty-tech-budget-presentation-lunenburg.pdf', 25,
    'FY 25 Budget Summary (Monty Tech)',
    ['FY2024', 'FY2025', 'DIFF'],
    {'Net School Spending': ['29486021', '30011216', '525195'],
     'Transportation': ['2399080', '2516010', '116930'],
     'Above Net School Spending': ['150000', '296948', '146948'],
     'Capital Budget ~ Equipment': ['490000', '460000', '-30000'],
     'Vehicles': ['10000', '50000', '40000'], 'BONDS': ['0', '0', '0'],
     'Total Budget': ['32535101', '33334174', '799073']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/monty-tech/'
    'final-monty-tech-budget-presentation-lunenburg.pdf', 29,
    'Contributions by Member City or Town (Monty Tech, FY25)',
    ['FY25 Enrollment', 'FY25 Contribution $'],
    {'Ashburnham': ['64', '594898'], 'Ashby': ['31', '326741'], 'Athol': ['104', '317289'],
     'Barre': ['45', '349180'], 'Fitchburg': ['386', '1789644'], 'Gardner': ['166', '963177'],
     'Harvard': ['9', '144440'], 'Holden': ['148', '1707486'], 'Hubbardston': ['32', '340398'],
     'Lunenburg': ['99', '1172061'], 'Petersham': ['12', '134917'], 'Phillipston': ['24', '244909'],
     'Princeton': ['25', '398251'], 'Royalston': ['11', '80006'], 'Sterling': ['66', '1098747'],
     'Templeton': ['87', '604478'], 'Westminster': ['71', '767439'], 'Winchendon': ['96', '614171'],
     'Total': ['1476', '11648232']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/monty-tech/'
    'final-prelim-fy25-budget-for-public-hearing-030624.pdf', 8,
    'General O&M Expenses (Monty Tech, FY25 prelim)',
    ['FY22 Expended', 'FY23 Expended', 'FY24 Approved', 'FY25 Proposed'],
    {'District Leadership': ['928604', '1160892', '1171797', '1279498'],
     'Instruction': ['15348625', '15858815', '16993242', '17219993'],
     'Student Services': ['3379194', '3891883', '3716631', '4047734'],
     'Operations & Maintenance': ['3527447', '3969960', '4010265', '4211094'],
     'Fixed Charges': ['4792513', '5303233', '5776116', '5745804'],
     'Fixed Assets': ['197577', '94234', '460000', '470000'],
     'Transfer to Reserves': ['35000', '35000', '40000', '40000'],
     'Tuition': ['321179', '317737', '367050', '320050'],
     'Total Expenses': ['28530138', '30631754', '32535101', '33334174']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/monty-tech/'
    'final-prelim-fy25-budget-for-public-hearing-030624.pdf', 8,
    'General Fund Income Received (Monty Tech, FY25 prelim)',
    ['FY21-22 Received', 'FY22-23 Received', 'FY24-25 Proposed'],
    {'Chapter 70': ['15489639', '17220222', '18362984'],
     'Transportation Reimbursement': ['1698452', '1809287', '1925000'],
     'School Building Authority Aid': ['0', '0', '0'],
     'Community Assessments': ['10527334', '11352418', '12446190'],
     'Interest Income': ['14673', '195309', '0'], 'Miscellaneous Receipts': ['276220', '109904', '0'],
     'Appropriation from E&D': ['550000', '600000', '450000'],
     'Fund Transfers': ['340000', '75000', '150000'],
     'Total General Fund Income': ['28896318', '31362140', '33334174']})

# Only the clean "SALARIES PEG ACCESS" subtotal is extracted; the sheet's "Calculations"
# chain (Salaries -> +Indirect -> +Operations -> +Capital) is real and reconciles (per the
# surveying agent) but is not transcribed here -- same reasoning as the FY24 PACC workbook
# above, one clean tying table is enough.
_rows(
    'budget-workbooks/finance-committee/fy25-budget/public-access-cable/'
    'fy25-working-sw-7.redacted.xlsx', 'sheet FY25 PEG ACCESS BUDGET',
    'Total Salaries PEG Access',
    ['FY23 BUDGETED', 'FY23 ACTUALS', 'FY24 BUDGETED', 'FY25 Approved BUDGET'],
    {'511000 Salaries PEG Access': ['87322.51', '55727.18', '83000', '92371.17'],
     '512105 P/R Videographers': ['25000', '26209.55', '27000', '33000'],
     '514002 Longevity': ['944.49', '944.49', '944.49', '1271.85'],
     'Total Salaries PEG Access': ['113267', '82881.22', '110944.49', '126643.02']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/school/'
    'nb-discussion-f-district-heating-issues-update-3-6-24.docx-1.pdf', 1,
    'District Heating Issues -- repair costs by building',
    ['Stated Subtotal'],
    {'Primary School': ['25244.00'], 'Turkey Hill': ['3451.00'], 'LMHS': ['44950.00'],
     'DISTRICT TOTAL': ['73645.00']})

_rows(
    'budget-workbooks/finance-committee/fy25-budget/sewer/revised-sewer-powerpoint-fy25.pdf', 10,
    'Planned FY 25 Equipment Upgrades',
    ['Cost'],
    {'Dana St. Pumps & Motors': ['70000'], 'Carbtrol Odor Control': ['2499'],
     'Line Repairs (Dana St.)': ['100000'], 'Leominster Rd. Seals': ['3000'],
     'Carbtrol Odor Control (Leominster Rd.)': ['2500'], 'Mass 1 Pumps & Motors': ['40000'],
     'Mass 1 Line Repairs': ['70000'], 'Mass 1 Seals': ['4000'], 'Mass 1 HMI Panel': ['12000'],
     'Mass 1 Dialer': ['4000'], 'Misc. Spares Pump': ['10000'],
     'Misc. Spares Vacuum Pumps': ['4000'],
     'Misc. Spares Dialers & Various Components': ['13000'], 'Contingency': ['33750'],
     'GRAND TOTAL': ['368749']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/sewer/revised-sewer-powerpoint-fy25.pdf', 16,
    'FY25 Enterprise Fund Budget -- Revenues',
    ['Amount'],
    {'User Charges': ['1230400'], 'Connection Fees': ['20000'], 'Sewer Bank Fees': ['5300'],
     'Permit Fees': ['3715'], 'Penalties & Interest': ['10000'], 'Investment Income': ['8000'],
     'Estimated Betterment Revenue': ['473774'],
     'Total Current Year Revenue and Available Funds': ['1751189']})
_rows(
    'budget-workbooks/finance-committee/fy25-budget/sewer/revised-sewer-powerpoint-fy25.pdf', 17,
    'Summary of FY25 Enterprise Fund Budget -- Expenses',
    ['Amount'],
    {'Payroll': ['92566.50'], 'Infrastructure Maintenance': ['87600'], 'Outsourcing': ['148155'],
     'Inflow/Infiltration Remediation': ['10000'], 'Utilities': ['42668'], 'Legal': ['4000'],
     'Engineering': ['30000'], 'Office Expenses': ['4025.80'], 'Capital Expenditures': ['368748.99'],
     'Debt Service to Leominster & Fitchburg': ['57656.64'],
     'Connection Fees due to Leominster & Fitchburg': ['7725'],
     'User Fees to Leominster & Fitchburg': ['859273.94'], 'Indirect Costs': ['90600.97'],
     'Betterment Debt Service': ['311668.16'], 'Total Expenditures': ['2114689']})

_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/fy26-facilities-budget.pptx',
    10,
    'FY25 Facilities Budget -- YTD Expended',
    ['FY2025 Budget', 'FY2025 YTD Through 1/8/25'],
    {'Electricity Charges': ['100000', '55643'], 'Heating Fuel - Oil': ['34861', '14982'],
     'Heating Fuel - Natural Gas': ['37040', '11870'], 'Water Charges': ['6695', '11065'],
     'Sewer Usage Fees': ['9857.10', '7430'], 'Rubbish Removal': ['18000', '10363'],
     'Facilities Salaries': ['231088', '151539'],
     'Contracted Services & Repairs': ['90000', '58588'],
     'New Line FY25 Purchase of Service': ['150000', '52456'],
     'Contracted Cleaning Services': ['86000', '34875'], 'Departmental Expenses': ['5492', '3064'],
     'Teen Center Expenses': ['10000', '8514'], 'Custodial Supplies': ['7166', '4874'],
     'Building MTC Supplies': ['15856.50', '14721'], 'Uniform Allowance': ['2200', '0'],
     'Town Sewer Betterment': ['76701', '0'], 'Totals': ['880956.60', '439984.00']})
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/fy26-facilities-budget.pptx',
    13,
    'FY 2025 Facilities Target Budget Changes',
    # Only FY2022 and FY2025 are kept: the FY2026 and $Increased columns do not reconcile
    # to the printed Totals row with the 16 line items transcribed here (both come up
    # short by exactly $1,000, suggesting an untranscribed or stale line item on the
    # slide, the same kind of staleness the surveying agent found in the analogous FY25
    # deck's "$ Increased" column) -- not forced.
    ['FY2022', 'FY2025'],
    {'Electricity Charges': ['130000', '100000'],
     'Heating Fuel - Oil': ['34861', '34861'],
     'Heating Fuel - Natural Gas': ['37040', '37040'],
     'Water Charges': ['6695', '6695'],
     'Sewer Usage Fees': ['9857.10', '9857.10'],
     'Rubbish Removal': ['17100', '18000'],
     'Facilities Salaries': ['221589.43', '231087.88'],
     'Contracted Services': ['225000', '90000'],
     'Purchase of Service': ['0', '150000'],
     'Contracted Cleaning Services': ['86000', '86000'],
     'Departmental Expenses': ['0', '5492'],
     'Teen Center Expenses': ['10000', '10000'],
     'Custodial Supplies': ['7166', '7166'],
     'Building MTC Supplies': ['15856.50', '15856.50'],
     'Uniform Allowance': ['2200', '2200'],
     'Town Sewer Betterment': ['76701', '71209'],
     'Totals': ['880066.03', '875464.48']})
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/fy26-facilities-budget.pptx',
    14,
    'FY 2024 Parks Target Budget Changes',
    ['FY2025', 'FY2026', '$ Increased'],
    {'Salary - Rec Director': ['25346.64', '29033.60', '3686.96'],
     'Salary - Beach Staff': ['20500', '24000', '3500'], 'Salary - Programming': ['5000', '5000', '0'],
     'Departmental Expenses': ['6400', '6400', '0'], 'Purchase of Service': ['60000', '70000', '10000'],
     'Totals': ['117246.64', '134433.60', '17186.96']})

_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-fire-dept-budget-presentation-online.pptx',
    7,
    'Response Breakdown 2024',
    ['Number'],
    {'Fires/Hazardous Cond.': ['163'], 'Alarms': ['171'], 'Service/Good Intent': ['113'],
     'EMS/Rescue': ['1193'], 'Inspections': ['414'], 'Other': ['29'], 'Total': ['2083']})

_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-public-access-cable-budget-presentation.pptm',
    11,
    'PACC Anticipated Income FY26',
    ['Amount'],
    {'Comcast Income': ['146226'], 'Town Interest': ['13000'], 'Inv Interest': ['35430'],
     'Retained Earn': ['0'], 'Total Income': ['194656']})
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-public-access-cable-budget-presentation.pptm',
    12,
    'Budget Request -- Salaries PEG Access Subtotal',
    ['ORIGINAL APPROP', 'FY2026 Request', 'Delta'],
    {'511000 Salaries Division/Dept': ['92371.17', '102100.00', '9728.83'],
     '512105 Payroll Videographers': ['33000.00', '38500.00', '5500.00'],
     '514002 Longevity Pay': ['1271.84', '1424.81', '152.97'],
     'Total 62001901 Salaries PEG Access E': ['126643.01', '142024.81', '15381.80']})
# Printed as "Revenue Total" / "Expense Total" / "Grand Total" -- all three contain
# 'total'. Reordered (Grand Total, Revenue Total, Expense Total) as a row identity: Grand
# Total - Revenue Total = Expense Total. The FY2026 Request column is excluded -- per the
# surveying agent it does not reconcile on this table (a different basis), only the
# ORIGINAL APPROP and Delta columns do.
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'fy26-public-access-cable-budget-presentation.pptm',
    12,
    'Budget Request -- Revenue/Expense/Grand Total',
    ['ORIGINAL APPROP', 'Delta'],
    {'Grand Total': ['-36935.02', '68576.16'], 'Revenue Total': ['-245708.00', '51052.45'],
     'Expense Total': ['208772.98', '17523.71']})


# ---------------------------------------------------------------------------------------
# Batch 3 (I3/I4 FY26 school-department and FY27 department-presentation decks).

_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'lunenburg-public-schools/copy-of-athletic-budget-user-fee-proposal-1-8-25.pdf', 2,
    'Current Impact -- FY26 Athletic Fees',
    ['FY24 Participation', 'Athletic Fee', 'Maximum Revenue @ Full Pay'],
    {'High School': ['616', '250', '154000.00'], 'Middle School': ['198', '200', '39600.00'],
     'MAX TOTAL': ['', '', '193600.00']})
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'lunenburg-public-schools/copy-of-athletic-budget-user-fee-proposal-1-8-25.pdf', 5,
    'Proposed Impact -- FY26 Athletic Fees',
    ['FY24 Participation', 'Proposed Fee', 'Maximum Revenue @ Full Pay'],
    {'High School': ['616', '325', '200200.00'], 'Middle School': ['198', '275', '54450.00'],
     'MAX TOTAL': ['', '', '254650.00']})

# Printed as "TOTAL EXPENSES" / "TOTAL SALARIES" / "TOTAL BUDGET" -- same three-way
# collision as the FY24 superintendent's budget table above; reordered (Budget, Expenses,
# Salaries) as a row identity.
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'lunenburg-public-schools/fy26-school-department-budget-fincom-3.20.25.pptx',
    2,
    'FY26 School Department Budget Summary',
    ['FY25 Budgeted', 'FY26 Budgeted'],
    {'TOTAL BUDGET': ['24883376', '25787474'], 'TOTAL EXPENSES': ['7695034', '9117566'],
     'TOTAL SALARIES': ['17188342', '16669908']})

# The bottom "TOTAL" row's FY25 Monthly Total figure is printed as $257,739.30, which does
# NOT equal the sum of the five FY25 plan totals ($277,775.94, a $20,036.64 gap) -- a real
# inconsistency in the source, left blank here rather than forced. Participants and the
# FY26 Monthly Total column both tie exactly.
_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/'
    'lunenburg-public-schools/health-insurance-1.pdf', 2,
    'FY26 Level Service and Needs Based Calculations -- Health Insurance by Plan',
    ['Participants', 'FY26 Monthly Total'],
    {'HMO Blue (Fam)': ['110', '233965.94'], 'HMO Blue (Ind)': ['32', '25879.61'],
     'Blue Care (Fam)': ['19', '49528.09'], 'Blue Care (Ind)': ['9', '8920.66'],
     'Blue Select': ['1', '703.59'], 'TOTAL': ['171', '318997.89']})

_rows(
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/presentation-fy26-budget.pptx',
    10,
    '541 Council on Aging -- FY2026 Budget Request',
    ['Original Approp', 'Revised Budget', 'FY2026 Request'],
    {'511000 Salaries Division/Dept': ['82219.68', '90221.92', '87053.04'],
     '511001 Salaries Clerical': ['37774.86', '37774.86', '41064.36'],
     '511002 Salaries Assistants': ['19807.88', '19807.88', '19825.74'],
     '511003 Salaries Staff': ['20278.12', '22825.78', '44254.08'],
     '511015 Outreach Worker': ['44626.25', '44872.63', '51785.24'],
     '512207 P/R Asst Outreach Worker': ['9632.85', '9632.85', '11010.70'],
     '514002 Longevity Pay': ['2509.36', '2671.82', '0'],
     'Salaries (subtotal)': ['216849.00', '227807.74', '254993.16'],
     '530000 Programs': ['5000.00', '5000.00', '7500.00'],
     '530100 MOC Nutrition': ['300.00', '300.00', '300.00'],
     '531012 Training': ['300.00', '300.00', '500.00'], '534400 Postage': ['400.00', '400.00', '400.00'],
     '534500 Advertising': ['500.00', '500.00', '0'],
     '540000 Office Supplies': ['2600.00', '2600.00', '3600.00'],
     '571000 Mileage Reimbursement': ['3674.00', '3674.00', '3800.00'],
     '573100 Meetings/School': ['500.00', '500.00', '0'],
     'Expenses (subtotal)': ['13274.00', '13274.00', '16100.00'],
     '541 Council on Aging (Total)': ['230123.00', '241081.74', '271093.16']})

_rows(
    'budget-workbooks/finance-committee/fy26-budget/parks-and-town-hall-presentations/'
    '2025-lmbdc-taylor-burns-design.pdf', 40,
    'Cost Estimate -- Trade Costs',
    ['Cost'],
    {'Meeting House Renovation': ['2624842'], 'Ritter Memorial Renovation': ['2068279'],
     'Town Hall': ['6937445'], 'Sitework': ['1657520'], 'Trade Costs (Total)': ['13288086']})

_rows(
    'budget-workbooks/finance-committee/fy26-budget/school-budget-presentation-pdf-copy.pdf', 14,
    'Position Count of Role / Sum of FTE (Reconciling Information: Positions Cut)',
    ['Count', 'Sum of FTE'],
    {'Assistant Principal': ['1', '1'], 'Behavioral Support': ['2', '2'],
     'Central Office': ['1', '1'], 'Custodian': ['5', '2.5'], 'Facilities': ['1', '1'],
     'Instructional Specialist/Coach/Tutor': ['2', '1.5'], 'IT': ['1', '0.5'],
     'Paraprofessional': ['9', '9'], 'Secretary': ['3', '2'], 'Teachers': ['12', '9.6'],
     'Athletics Dep': ['2', '2'], 'Grand Total': ['39', '32.1']})
_rows(
    'budget-workbooks/finance-committee/fy26-budget/school-budget-presentation-pdf-copy.pdf', 24,
    'Reconciling Information: School Salaries -- Building Slides',
    ['fy25', 'fy26'],
    {'Central Office Personnel Slide': ['885052', '940462'], 'PS - Slide 4': ['3677878', '3400225'],
     'ES - Slide 5': ['3428747', '2801334'], 'MS - Slide 6': ['3818859', '3873665'],
     'HS - Slide 7': ['4980982', '4606390'], 'Building Slides Total': ['16791518', '15622076']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/coa/fy27-budget-presentation-coa.pptx',
    6,
    'FY27 Council on Aging Budget',
    ['FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY25 Actual', 'FY26 Origin Approp', 'FY2027'],
    {'Senior Center Director Salary': ['82489.69', '87478.40', '82219.68', '100552.43', '87053.04', '87053.04'],
     'COA Clerical': ['37797.76', '36995.02', '37774.86', '37658.04', '41064.36', '41064.36'],
     'Salary Asst Meal Site Manager': ['20416.32', '9759.28', '19807.88', '12110.24', '19825.74', '19824.50'],
     'Meal Site Manager Salary': ['20278.12', '18470.49', '20278.12', '15858.48', '44254.08', '47200.56'],
     'Outreach Worker': ['43380.40', '45789.12', '44626.25', '49912.75', '51785.24', '50290.00'],
     'P/R Asst Outreach Worker': ['9063.60', '7773.60', '9632.85', '9956.08', '0', '0'],
     'Longevity Pay': ['2367.46', '2575.25', '2509.36', '2811.28', '0', '0'],
     'Payroll (subtotal)': ['215793.35', '208841.16', '216849.00', '228859.30', '243982.46', '245432.46'],
     'Programs COA': ['5000.00', '4350.00', '5000.00', '4532.38', '8000.00', '8000.00'],
     'MOC Nutrition': ['300.00', '300.00', '300.00', '300.00', '500.00', '500.00'],
     'Training': ['300.00', '30.00', '300.00', '215.00', '800.00', '800.00'],
     'Advertising': ['500.00', '466.00', '500.00', '0', '500.00', '0'],
     'Office Supplies': ['2600.00', '2322.60', '2600.00', '3074.18', '3600.00', '3950.00'],
     'Kitchen Supplies': ['0', '0', '0', '0', '0', '1500.00'],
     'Mileage Reimbursement': ['3674.00', '3656.71', '3674.00', '2739.68', '3800.00', '1000.00'],
     'Meetings/School': ['500.00', '320.00', '0', '0', '0', '0'],
     'Expense (subtotal)': ['12874.00', '11445.31', '12374.00', '10861.24', '17200.00', '15750.00'],
     'Total Council on Aging': ['228667.35', '220286.47', '229223.00', '239720.54', '261182.46', '261182.46']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/general-government/'
    'fy27-budget-presentation-land-use.pptx',
    6,
    'FY27 Land Use Budget',
    ['FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY25 Actual', 'FY2026', 'FY2027'],
    {'Planning Board Director': ['108177.68', '39736.80', '108177.68', '70272.00', '106374.80', '112723.00'],
     'Salaries Clerical': ['112217.39', '101330.31', '118436.46', '47471.76', '130563.67', '117869.07'],
     'Salaries Staff': ['5000.00', '222.75', '5000.00', '893.62', '5000.00', '5000.00'],
     'Building Commissioner': ['97359.91', '89665.17', '87148.04', '113818.52', '100681.88', '106636.83'],
     'Conservation Administrator': ['48095.56', '45101.33', '68262.00', '63175.58', '72137.06', '80684.43'],
     'Longevity Pay': ['4700.00', '2350.00', '2350.00', '2350.00', '2350.00', '0'],
     'Mileage Stipend': ['7500.00', '7499.96', '7500.00', '7500.00', '7500.00', '7500.00'],
     'Salary (subtotal)': ['383050.54', '285906.32', '396874.18', '305481.48', '424607.41', '430413.33'],
     'Recordings-Registry of Deeds': ['150', '0', '150', '0', '150.00', '150.00'],
     'Publications': ['2100.00', '1002.41', '2100.00', '786.45', '2100.00', '2100.00'],
     'Printing-Planning': ['300', '110', '300', '80', '0', '0'],
     'Purchase of Service': ['650', '61', '650', '0', '0', '2000.00'],
     'Advertising': ['2250.00', '3681.27', '3750.00', '1290.00', '2250.00', '2250.00'],
     'Office Supplies': ['2560.00', '1581.15', '2660.00', '369.37', '2600.00', '2600.00'],
     'Uniform Allowance Reimbursement': ['360', '336', '360', '350', '900.00', '900.00'],
     'Mileage Reimbursement': ['285', '241.51', '850', '692.52', '1350.00', '1350.00'],
     'Dues/Membership': ['1066.00', '325', '1066.00', '371', '1150.00', '1150.00'],
     'Meetings/School': ['3409.00', '1235.14', '3409.00', '2134.00', '5050.00', '5050.00'],
     'Expenses (subtotal)': ['13130.00', '8573.48', '15295.00', '6073.34', '15550.00', '17550.00'],
     'Total - Land Use': ['396180.54', '294479.80', '412169.18', '311554.82', '440157.41', '447963.33']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/'
    'fy26-suzor-services-agreement.pdf', 2,
    'FY26 Renewal of Services -- Pricing Proposal',
    ['Qty', 'Your Price', 'Total'],
    {'Gov IT Dept - Gov Add-On Workstation - Gov Plan 3': ['90', '913.71', '82233.90'],
     'Help Desk Onsite Support': ['2080', '35.11', '73028.80'], 'Total': ['', '', '155262.70']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/'
    'fy26-suzor-services-agreement.pdf', 13,
    'Suzor Services Q3 FY26 -- Pricing Proposal',
    ['Qty', 'Your Price', 'Total'],
    {'Help Desk Onsite Support': ['416', '35.11', '14605.76'],
     'Gov IT Dept - Gov Add-On Workstation - Gov Plan 3': ['23', '913.71', '21015.33'],
     'Total': ['', '', '35621.09']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/'
    'munis-contract-12.4.24.pdf', 17,
    'Investment Summary -- Summary',
    ['One Time Fees', 'Recurring Fees'],
    {'Total Tyler License Fees': ['0', '0'], 'Total Saas': ['0', '108567.00'],
     'Total Tyler Services': ['5428.00', '0'],
     'Total Third-Party Hardware, Software, Services': ['0', '0'],
     'Summary Total': ['5428.00', '108567.00']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/'
    'munis-contract-12.4.24.pdf', 18,
    'Contract Total (Munis)',
    ['Amount'],
    {'Recurring Fees (Net Annual SaaS, Year 1)': ['108567.00'],
     'One Time Fees (Professional Services)': ['5428.00'], 'Contract Total': ['113995.00']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/open-gov.pdf', 2,
    'Customer Billing/Service Periods',
    # Transposed from how the page prints it (one row per billing period, with that
    # period's own Total as its last column) to rows=fee categories/columns=periods, so
    # the single 'Total' row is the one this checker's additive path expects; the figures
    # are unchanged.
    ['11/01/2025', '11/01/2026', '11/01/2027'],
    {'Contractor License Verification': ['992.25', '1041.86', '1093.96'],
     'Esri ArcGIS Integration': ['1323.00', '1389.15', '1458.61'],
     'MAT/Assessor System & Flags': ['2646.00', '2778.30', '2917.22'],
     'Permitting and Licensing - 3 Service Areas': ['32472.58', '34096.21', '35801.02'],
     'Total': ['37433.83', '39305.52', '41270.81']})


# ---------------------------------------------------------------------------------------
# Batch 4 (I4 FY27 department-presentation decks -- PACC, preliminary budget, unclassified,
# triboard facilities/fire).

# Only the Revenue Total / Expense Total / Grand Total identity is kept -- the raw
# 62001901/62001902/62001904 line items are left out, because "Revenue Total" is just the
# single 62001904 line restated and "Expense Total" is 62001901+62001902; including all
# three raw lines alongside their own totals would double-count in the additive path.
# Order (Revenue Total, Expense Total, Grand Total): Revenue Total - Expense Total =
# Grand Total (Delta), verified for both columns.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/pacc/'
    'fy27-budget-worksheets-pacc-fy26-fy27-comparison-contingency-rev2.redacted.xlsx',
    'sheet 190 PEG ACCESS',
    'FY27 PAC Contingency Budget Rev 2 -- Revenue/Expense/Grand Total',
    ['FY2026 Budget', 'FY2027 Request'],
    {'Revenue Total': ['194000', '200000'], 'Expense Total': ['226296.6936', '306206.41'],
     'Grand Total (Delta)': ['-32296.6936', '-106206.41']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/pacc/'
    'fy27-budget-worksheets-pacc-fy26-fy27-comparison.redacted.xlsx',
    'sheet 190 PEG ACCESS',
    'FY27 PAC Budget -- Revenue/Expense/Grand Total',
    ['FY2026 Budget', 'FY2027 Request'],
    {'Revenue Total': ['194000', '200000'], 'Expense Total': ['226296.6936', '297506.41'],
     'Grand Total (Delta)': ['-32296.6936', '-97506.41']})

# This earlier draft's "FY 2027 Expenditure Summary" duplicates figures already extracted
# from the later updated-budget-fincom-3.26.27.pptx exactly (same FY27 Preliminary column)
# and is not re-listed; its Local Receipts table differs from that later deck's ($3,360,524
# vs $3,535,524) and is a genuine earlier draft, extracted here.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/'
    'preliminary-budget-presentation-2.19.26/'
    'preliminary-budget-presentation-2.19.26-final-v.2.27.26.pptx',
    9,
    'FY 2027 Local Receipts Estimate',
    ['FY25 Actual', 'FY26 Budget', 'FY27 Budget'],
    {'Motor Vehicle Excise': ['2190195.56', '1875000', '1875000'],
     'Meal & Cannabis Excise': ['160458.23', '125000', '125000'],
     'Penalties/Interest on Taxes and Excises': ['141872.02', '140000', '140000'],
     'PILOT': ['1605.75', '1600', '1600'], 'Fees': ['202017.87', '180000', '180000'],
     'Dept. Revenue-Schools': ['183945.08', '61411', '61411'],
     'Dept. Revenue Cemetery Burials': ['3800.00', '3500', '3500'],
     'Other Departmental Revenue (Ambulance)': ['481173.92', '275000', '275000'],
     'Licenses/Permits': ['353444.01', '350000', '350000'],
     'Special Assessments (Trailer Parks)': ['26592.00', '12000', '12000'],
     'Fines and Forfeits': ['17432.57', '12013', '12013'],
     'Investment Income': ['588996.51', '100000', '100000'],
     'Misc. Non-Recurring': ['280843.25', '225000', '225000'],
     'Total (stated on FY 2027 Revenues slide, not a grid row)': ['', '', '3360524.00']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/unclassified/'
    'draft-fy-27-general-govrernment-unclassified-budget-presentation-insurances-workers-comp-'
    'fica-budget-presentation-3.12.26.pptx',
    2,
    'General Government -- Unclassified FY27 Summary',
    ['FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY25 Actual', 'FY26 Budget', 'FY2027'],
    {'Liability Insurance': ['248986.44', '226513.65', '249188.81', '233635.91', '239188.81', '230000.00'],
     'Workers Compensation': ['161882.28', '122983.00', '169976.39', '118079.95', '145000.00', '135000.00'],
     'Group Health Insurance': ['2957469.53', '2536638.99', '3059912.01', '2773391.29', '3298520.32', '3695424.59'],
     'Life Insurance': ['15000.00', '15401.19', '15000.00', '17556.06', '15000.00', '20000.00'],
     'Unemployment Compensation': ['10000.00', '11196.00', '10000.00', '217.87', '10000.00', '10000.00'],
     'Medicare': ['341070.00', '342349.51', '375177.00', '346827.88', '400000.00', '410000.00'],
     'TOTAL GEN. GOV. UNLASSIFIED': ['3734408.25', '3255082.34', '3879254.21', '3489708.96', '4107709.13', '4500424.59']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/decision-aids/override-on-a-page.pptx',
    1,
    'Revenue Projections (Override on a Page)',
    ['Amount'],
    {'Property Tax': ['36332933.80'], 'Local Receipts': ['3360524.00'], 'Enterprise Funds': ['338397.19'],
     'Cherry Sheet - State Aid Receipts': ['11404917.00'],
     'Cherry Sheet - Offset Receipts (School Choice)': ['-77329.00'],
     'Cherry Sheet - Offset Receipts (Library Sweeps)': ['-34818.00'],
     'Cherry Sheet Assessments': ['-1069349.00'], 'Assessors Overlay': ['-260000.00'],
     'Levy Appropriated to Capital Plan': ['-244576.00'], 'Total': ['49750699.99']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/fy27-facilities-budget-for-triboard.pptx',
    18,
    'Projected Facilities Budget Changes Through FY 2029',
    ['FY2022', 'FY2023', 'FY2024', 'FY2025', 'FY2026', 'FY2027', 'FY2028', 'FY2029'],
    {'Electricity Charges': ['130000', '130000', '100000', '100000', '100000', '117000', '118000', '119000'],
     'Heating Fuel-Oil': ['34861', '34861', '34861', '34861', '39000', '39000', '39500', '40000'],
     'New Line-Generator Fuel': ['0', '0', '0', '0', '1000', '1000', '1000', '1000'],
     'Heating Fuel-Natural Gas': ['37040', '37040', '37040', '37040', '38500', '68000', '68000', '70000'],
     'Water Charges': ['6695', '6695', '6695', '6695', '14000', '17000', '17500', '18000'],
     'Sewer Usage Fees': ['9857.10', '9857.10', '9857.10', '9857.10', '9857.10', '15000', '15500', '16000'],
     'Rubbish Removal': ['17100', '17100', '17100', '18000', '19000', '24000', '24500', '25000'],
     'Facilities Salaries': ['221589.43', '221589.43', '226673.65', '231087.88', '259166.70', '265645.87', '272287.02', '308094.19'],
     'Contracted Services': ['225000', '225000', '240000', '90000', '90000', '100000', '102500', '105062.50'],
     # This row's 7 printed figures align to FY2023-FY2029 (FY2022 has no entry at all),
     # proven by the Totals row: including the figure in FY2024 instead of FY2023 (the
     # other plausible alignment) overshoots the printed FY2024 Total by exactly $150,000
     # and undershoots FY2029 by exactly $168,100 -- this alignment is the one that ties.
     'Purchase of Service(repairs)': ['', '0', '0', '150000', '150000', '160000', '164000', '168100'],
     'Contracted Cleaning Services': ['86000', '86000', '86000', '86000', '80000', '86000', '86000', '86000'],
     'TCP Expenses': ['0', '0', '0', '0', '27000', '27000', '27000', '27000'],
     'Departmental Expenses': ['0', '0', '5492', '5492', '5492', '5500', '5500', '5500'],
     'Teen Center Expenses': ['10000', '10000', '10000', '10000', '10000', '12000', '12000', '12000'],
     'Custodial Supplies': ['7166', '7166', '7166', '7166', '8200', '10000', '10000', '10250'],
     'Building MTC Supplies': ['15856.50', '15856.50', '15856.50', '15856.50', '12000', '20000', '20000', '20500'],
     'Uniform Allowance': ['2200', '2200', '2200', '2200', '2200', '2200', '2200', '2200'],
     'Town Sewer Betterment': ['76701', '76701', '76701', '71209', '67547', '65717', '63886', '0'],
     'Totals': ['880066.03', '885558.03', '875642.25', '875464.48', '932962.80', '1035062.87', '1049373.02', '1033706.69']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/fy27-facilities-budget-for-triboard.pptx',
    19,
    'Projected Parks Budget Changes Through FY 2029',
    ['FY2027', 'FY2028', 'FY2029'],
    {'Salary-Rec Director': ['29033.60', '29759.44', '61006.85'],
     'Salary-Beach Staff': ['25000', '25625', '26265.63'], 'Salary-Programming': ['7500', '7500', '7500'],
     'Departmental Expenses': ['6400', '6400', '6400'], 'Purchase of Service': ['80000', '90000', '10000'],
     'Totals': ['147933.60', '159284.44', '111172.48']})
# Split into two table_title groups (same slide) so Utilities' own total and Building
# Maintenance's own total each tie against only their own line items, rather than being
# merged into one group where the additive check would sum both sections together.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/fy27-facilities-budget-for-triboard.pptx',
    15,
    'TCP Budget Cost-tracking -- Utilities',
    ['Revised Budget'],
    {'Utilities - Electricity': ['26000'], 'Natural Gas': ['25000'], 'Water': ['1500'],
     'Sewer': ['1500'], 'Trash': ['2500'], 'Phones': ['0'], 'Internet': ['6216'],
     'Utilities Total': ['62716']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/fy27-facilities-budget-for-triboard.pptx',
    15,
    'TCP Budget Cost-tracking -- Building Maintenance',
    ['Revised Budget'],
    {'Building Maint - Service Boilers': ['1000'], 'Fire Extinguisher': ['400'],
     'Fire Alarm Inspect': ['400'], 'Fire Alarm Monitoring': ['500'], 'Burglary Alarm': ['900'],
     'Boiler Certificates': ['200'], 'PM Generator': ['700'], 'Generator Fuel': ['0'],
     'Fire Suppression Inspect': ['800'], 'Landscaping': ['15000'], 'Snow Removal': ['0'],
     'Cleaning/Custodial': ['5000'], 'Building Maint Total': ['24900']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/fire-fy-27-budget-presentation-2nd-draft.pptx',
    4,
    'Response Breakdown 2024 (Fire, 2nd draft)',
    ['Number'],
    {'Fires/Hazardous Cond.': ['163'], 'Alarms': ['171'], 'Service/Good Intent': ['113'],
     'EMS/Rescue': ['1193'], 'Inspections': ['414'], 'Other': ['29'], 'Total': ['2083']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/fire-fy-27-budget-presentation-2nd-draft.pptx',
    # Each line item is its own slide (the "(+$X)" increase shown beside that line's new
    # total), and the consolidated "Total Increase- Expenses -$32,000" is a fifth, separate
    # slide -- the table spans all five.
    '15-19',
    'FY\'27 Expense Total Increase (Fire)',
    ['Amount'],
    {'EMS Supply': ['12000'], 'Capital Replacement': ['5000'], 'Radio Maintenance': ['5000'],
     'Vehicle Maintenance': ['10000'], 'Total': ['32000']})


# ---------------------------------------------------------------------------------------
# Batch 5 (I4 triboard-material per-department decks, FY27).

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'july-8-2025-tri-board-meeting-materials.pdf', 20,
    '4th Shift -- Estimated Costs',
    ['Amount'],
    {'3 New FF/PM': ['209761.35'], '4th Shift Officer': ['11327'], 'Overtime Increase': ['80386.02'],
     'Holiday Increase': ['22325.33'], 'Uniform': ['3300'], 'Est. OPEB Costs': ['137269.56'],
     'Estimated Cost (Total, p.20)': ['464369.26']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'lunenburg-public-schools-fiscal-year-2027-2028-and-2029-budget-projections.pptx',
    38,
    'FY26 Budget Summary (LPS)',
    ['Amount'],
    {'Salaries': ['17110394'], 'Expenses': ['9177080'], 'Total FY26 Budget': ['26287474']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'lunenburg-public-schools-fiscal-year-2027-2028-and-2029-budget-projections.pptx',
    44,
    'FY27/FY28 Budget Summary (LPS; FY29 excluded, see below)',
    ['FY27', 'FY28'],
    {'Salaries': ['17376401', '17767838'], 'Expenses': ['9875772', '10695991'],
     'Total': ['27252173', '28463829']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/preliminary-revenue-presentation.pptx',
    2,
    'FY 2027 Revenues',
    ['Amount'],
    {'Property Tax': ['36332933.80'], 'State Aid': ['11244422.00'], 'Local Receipts': ['3754021.19'],
     'Total': ['51331376.99']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/preliminary-revenue-presentation.pptx',
    9,
    'FY 2027 Non-Appropriated Expenses',
    ['Amount'],
    {'Offset Receipts': ['141054.00'], 'Overlay': ['260000.00'], 'State Assessments': ['1003251.00'],
     'Tax Title': ['0'], 'Non-Appropriated Expenses (Total)': ['1404305']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/preliminary-revenue-presentation.pptx',
    12,
    'FY 2027 Potential Revenue Distribution Scenario',
    ['Amount'],
    {'School': ['696521.74'], 'Town': ['573490.90'], 'Monty Tech': ['36047.25'],
     'TOTAL NEW FY27 REVENUE': ['1306059.89']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/revenue-v.-large-fixed-increases.pptx',
    2,
    'FY 2027 Revised Revenues',
    ['Amount'],
    {'Property Tax': ['36332933.80'], 'State Aid': ['11404917.00'], 'Local Receipts': ['3754021.19'],
     'Total': ['51491871.99']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/revenue-v.-large-fixed-increases.pptx',
    6,
    'FY 2027 Potential Revenue Distribution Scenario (revised)',
    ['Amount'],
    {'School': ['762279.76'], 'Town': ['627633.68'], 'Monty Tech': ['39450.44'],
     'TOTAL NEW FY27 REVENUE': ['1429363.89']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-library-presentation-for-fy27-and-on.pptx',
    5,
    'Anticipated FY27 Budget (Library)',
    ['FY25', 'FY26', 'FY27 Anticipated'],
    {'16101 Salaries': ['389559.77', '436215.76', '462405.61'],
     '16102 Expenses': ['194330.00', '195821.00', '208737.00'],
     '610 Lunenburg Public Library (Total)': ['583889.77', '632036.76', '671142.61']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-library-presentation-for-fy27-and-on.pptx',
    9,
    'Library Materials Expenditures',
    ['Budget FY26', 'FY27 Anticipated'],
    {'Physical Items': ['41650.00', '46950.00'], 'Software': ['3900.00', '4000.00'],
     'Databases, Online Resources': ['53687.00', '55987.00'], 'TOTAL': ['99237.00', '106937.00']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-library-presentation-for-fy27-and-on.pptx',
    11,
    'Office Supplies Expenditures (Library)',
    ['Previous Expense Total', 'FY27 Anticipated Need'],
    {'Demco': ['1049.26', '2110.00'], 'WB Mason': ['3286.23', '3470.00'],
     '2 Ricoh toners': ['160.00', '160.00'], '10,000 barcodes': ['410.00', '410.00'],
     'library card order': ['189.00', '200.00'], 'Stationary/business cards': ['440.00', '250.00'],
     'Blanks for demos/marketing': ['819.00', '900.00'], 'Gallery Supplies': ['1125.00', '500.00'],
     'Total': ['7478.49', '8000.00']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-accountant.pptx',
    8,
    'Preliminary Budget Projection (Accountant)',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['226882.62', '239608.89', '240564.30', '255102.01', '273194.20', '258814.34', '265272.69', '271892.51'],
     'Expenses': ['2070.78', '3750.00', '42862.53', '4800.00', '50050.00', '84150.00', '11475.00', '11475.00'],
     'Town Accountant (Total)': ['228953.40', '243358.89', '283426.83', '259902.01', '323244.20', '342964.34', '276747.69', '283367.51']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-assessing.pptx',
    7,
    'Preliminary Budget Projection (Assessing)',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['147300.83', '132726.96', '116887.49', '187392.16', '190159.23', '196115.69', '200993.58', '205993.42'],
     'Expenses': ['80046.36', '99980.00', '124568.96', '101930.00', '107149.00', '113963.00', '115102.63', '116253.66'],
     'Assessors (Total)': ['227347.19', '232706.96', '241456.45', '289322.16', '297308.23', '310078.69', '316096.21', '322247.08']})

# Columns reordered (Prelim Budget, FY26 Budget, FY27%, FY27$) so the three $ columns
# resolve in the order (minuend, subtrahend, difference): Prelim - FY26 Budget = FY27$.
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-health-insurance-1.pptx',
    20,
    'Budget History & FY 27 Preliminary and Beyond -- Total Health Ins. Line',
    ['FY27 Prelim Budget', 'FY26 Budget', 'FY27%', 'FY27$'],
    {'Total Health Ins. Line': ['3777514.51', '3298520.32', '14.52%', '478994.19']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-health-insurance.pptx',
    20,
    'Budget History & FY 27 Preliminary -- Total Health Ins. Line',
    ['FY25 Budget', 'FY26 Budget', 'FY24 Actual'],
    {'Health Insurance': ['1219887.00', '1315270.05', '923118.18'],
     'Insurance Cost Control': ['8000.00', '8000.00', '8000.00'],
     'Town Retiree Health': ['420343.79', '453214.67', '384372.97'],
     'School Retiree Health': ['1411181.22', '1521535.59', '1221147.84'],
     'PEC Expenses': ['500.00', '500.00', ''],
     'Total Health Ins. Line': ['3059912.01', '3298520.32', '2536638.99']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-health-services.pptx',
    8,
    'Preliminary Budget Projection (Health Services)',
    ['FY23 Budget', 'FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'General Health Expense': ['44651.80', '45517.88', '46332.44', '48533.56', '53427.16', '56630.56', '57881.87', '59228.92', '60609.64'],
     'Nashoba Health': ['36759.84', '36759.84', '39516.83', '39516.83', '43468.51', '47815.37', '52596.91', '57856.60', '63642.26'],
     'Nashoba Nursing': ['16848.26', '16848.26', '18111.88', '18111.88', '19923.07', '21915.37', '24106.91', '26517.60', '29169.36'],
     'Health Services (Total)': ['98259.90', '99125.98', '103961.15', '106162.27', '116818.74', '126361.30', '134585.68', '143603.12', '153421.25']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-it.pptx',
    5,
    'Preliminary Budget Projection (IT)',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries (Tech Admin Support)': ['7470.00', '24529.15', '25314.04', '25516.30', '56945.98', '59459.33', '60945.81', '62469.46'],
     'Expenses': ['188634.60', '257640.00', '241261.72', '359222.10', '442656.06', '530765.43', '543072.07', '555686.37'],
     'IT (Total)': ['196104.60', '282169.15', '266575.76', '384738.40', '499602.04', '590224.76', '604017.88', '618155.83']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-land-use-v.2.pptx',
    9,
    'Preliminary Budget Projection (Land Use)',
    ['FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['424608.00', '430413.32', '440989.39', '451826.55'],
     'Expenses': ['15550.00', '15550.00', '15705.50', '15862.56'],
     'Land Use (Total)': ['440158.00', '445963.32', '456694.89', '467689.11']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-presentation-misc.-general-government.pptx',
    3,
    'Preliminary Budget Projection -- Finance Committee (tri-board, Jan 12 2026 draft)',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Advertising': ['90.00', '100.00', '97.35', '100.00', '100.00', '125.00', '125.00', '125.00'],
     'Dues/Membership': ['184.00', '200.00', '190.00', '200.00', '200.00', '200.00', '200.00', '200.00'],
     'Meetings/School': ['376.94', '1000.00', '1326.42', '1500.00', '1500.00', '1000.00', '1000.00', '1000.00'],
     'Finance Committee (Total)': ['650.94', '1300.00', '1613.77', '1800.00', '1800.00', '1325.00', '1325.00', '1325.00']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-presentation-misc.-general-government.pptx',
    8,
    'Preliminary Budget Projection -- Central Purchasing (tri-board)',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim'],
    {'Office Equipment MTC': ['5752.91', '7500.00', '5892.90', '7500.00', '7500.00', '9000.00'],
     'Managed Print Services': ['22439.06', '26800.00', '19240.16', '26800.00', '27000.00', '27000.00'],
     'Postage': ['722.00', '3000.00', '3938.77', '3000.00', '50000.00', '50000.00'],
     'Central Purchasing (Total)': ['28913.97', '37300.00', '29071.83', '37300.00', '84500.00', '86000.00']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-town-clerk.pptx',
    7,
    'Preliminary Budget Projection -- Town Clerk',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['40314.72', '40756.60', '44558.68', '47859.80', '133502.08', '137056.05', '140556.82', '144037.49'],
     'Expenses': ['9997.13', '13258.17', '8676.17', '11900.00', '10100.00', '10900.00', '10100.00', '10100.00'],
     'Town Clerk (Total)': ['50311.85', '54014.77', '53234.85', '59759.80', '143602.08', '147956.05', '150656.82', '154137.49']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-town-clerk.pptx',
    7,
    'Preliminary Budget Projection -- Elections',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries (Election Workers)': ['2457.27', '8825.00', '7873.57', '8825.00', '3900.00', '8825.00', '3900.00', '8825.00'],
     'Expenses': ['6540.51', '7710.00', '7504.82', '8700.00', '7200.00', '12750.00', '11750.00', '11750.00'],
     'Elections (Total)': ['8997.78', '16535.00', '15378.39', '17525.00', '11100.00', '21575.00', '15650.00', '20575.00']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-town-clerk.pptx',
    8,
    'Preliminary Budget Projection -- Registration and Census',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim'],
    {'Salaries': ['17251.15', '19400.00', '16741.50', '19400.00', '19400.00', '19400.00'],
     'Expenses': ['325.00', '1550.00', '5876.38', '1550.00', '1550.00', '2050.00'],
     'Registration and Census (Total)': ['17576.15', '20950.00', '22617.88', '20950.00', '20950.00', '21450.00']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-presentation-town-manager-and-select-board.pptx',
    7,
    'Preliminary Budget Projection -- Select Board',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['129739.59', '147148.18', '164366.92', '141392.68', '159980.32', '171852.68', '176149.00', '180552.72'],
     'Expenses': ['4803.35', '7140.00', '6088.82', '9100.00', '20800.00', '29756.00', '29756.00', '29756.00'],
     'Select Board (Total)': ['134542.94', '154288.18', '170455.74', '150492.68', '180780.32', '201608.68', '205905.00', '210308.72']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/'
    'tri-board-presentation-town-manager-and-select-board.pptx',
    8,
    'Preliminary Budget Projection -- Town Manager',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['150779.49', '157715.00', '158928.19', '157715.00', '169125.00', '233353.00', '300686.83', '308204.00'],
     'Expenses': ['14871.67', '16000.00', '17241.93', '16200.00', '136200.00', '149000.00', '145650.00', '152737.50'],
     'Town Manager (Total)': ['165651.16', '173715.00', '176170.12', '173915.00', '305325.00', '382353.00', '446336.83', '460941.50']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-treasurer-collector.pptx',
    7,
    'Preliminary Budget Projection -- Treasurer',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['85720.49', '92656.56', '99584.20', '101318.88', '107491.49', '123430.33', '127516.09', '130678.99'],
     'Expenses': ['2044.56', '10475.00', '2853.65', '10475.00', '11475.00', '11475.00', '11475.00', '11475.00'],
     'Treasurer (Total)': ['87765.05', '103131.56', '102437.85', '111793.88', '118966.49', '134905.33', '138991.09', '142153.99']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-treasurer-collector.pptx',
    8,
    'Preliminary Budget Projection -- Tax Title/Foreclosure',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Purchase of Service': ['15724.47', '20500.00', '10982.67', '20500.00', '22000.00', '22000.00', '22000.00', '22550.00'],
     'Recordings-Reg. of Deeds': ['3885.00', '7000.00', '2205.00', '7000.00', '7000.00', '7000.00', '7000.00', '7175.00'],
     'Advertising': ['400.00', '1500.00', '350.00', '1500.00', '1500.00', '1500.00', '1500.00', '676.50'],
     'Tax Title/Foreclosure (Total)': ['20009.47', '29000.00', '13537.67', '29000.00', '30500.00', '30500.00', '30500.00', '30401.50']})
_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-treasurer-collector.pptx',
    8,
    'Preliminary Budget Projection -- Collector',
    ['FY23 Actual', 'FY24 Budget', 'FY24 Actual', 'FY25 Budget', 'FY26 Budget', 'FY27 Prelim', 'FY28', 'FY29'],
    {'Salaries': ['79677.80', '86965.24', '92866.71', '95699.48', '105937.83', '115596.09', '118473.50', '121422.83'],
     'Expenses': ['8505.64', '18900.00', '9249.79', '18900.00', '18900.00', '18900.00', '18900.00', '18900.00'],
     'Collector (Total)': ['88183.44', '105865.24', '102116.50', '114599.48', '124837.83', '134496.09', '137373.50', '140322.83']})

_rows(
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/tri-board-presentation-vso.pptx',
    8,
    'FY 2027 Preliminary Budget (Veterans Services)',
    ['FY26 Budget', 'FY27 Prelim Budget'],
    {'Salaries': ['11000.00', '11000.00'],
     'Expenses (Office Supplies, Veterans Graves, Memorial Day)': ['2699.00', '2699.00'],
     'Expenses (Veterans Benefits)': ['77000.00', '77000.00'],
     'Veterans Administration (Total)': ['90699.00', '90699.00']})


# ---------------------------------------------------------------------------------------
# NOT_EXTRACTED: every candidate_for_extraction=yes document that was examined and found
# NOT to carry a table worth extracting, with the specific reason (rule 13c: a pattern
# that does not match is not an absence -- each of these was actually opened and read, not
# inferred from its has_table/why fields, which is exactly the generic signal this task
# exists to go beyond). One of four reasons, always:
#   'no printed total'       -- real figures, nothing ties them together
#   'figures are pictures'   -- the numbers are in an embedded image/chart, not text
#   'duplicate of <key>'     -- the SAME figures (by content, not filename) are already
#                               extracted from, or registered against, <key>
#   'narrative not tabular'  -- prose/letter/contract/Q&A/calendar with no row-column
#                               structure and no repeated identity pattern
NOT_EXTRACTED = {
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/pre-fy26-budget-s.pptx':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/triboard-material/'
        'pre-fy26-budget-s-police.pptx (byte-identical extracted text under a different '
        'filename and sha256 -- detected by comparing the two documents\' own content, not '
        'their names)',

    # --- batch 1 ---
    'budget-workbooks/finance-committee/fy24-budget/20230309-dpw-and-facilities/fy24-dpw-budget-presentation-1.pptx':
        'figures are pictures -- every slide carrying budget numbers ("FY 24 Budget '
        'Request", "FY24 Budget Allocation", "General Highway", "Highway Labor", "Snow '
        'Removal", "Vehicle Maintenance", "Cemetery Department") shows <p:pic> True / '
        '<a:tbl> False in the pptx XML; extracted text is title-only',
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230322-admin-unclassified-and-debt-service-monty-tech-and-lps/lps/'
    '2023-0201-fy23-budget-quarterly-update.pdf':
        'no printed total -- a Grand Total IS printed (page 7) over roughly 267 individual '
        'MUNIS account lines across 7 ORG OBJ sections, but transcribing and independently '
        'verifying all 267 rows by hand is not practical at this scale and was not done '
        'here, so the tie is not proven by this survey and the table is not extracted',
    'budget-workbooks/finance-committee/fy24-budget/'
    '20230323-pacc-sewer-fire-and-other-moneyed-articles/pacc/fincomm-pres-24-final.pptm':
        'duplicate of budget-workbooks/finance-committee/fy24-budget/'
        '20230323-pacc-sewer-fire-and-other-moneyed-articles/pacc/'
        'paccdraft-1-version-3.redacted.xlsx (every tie-able figure in this pptm -- PACC '
        'Anticipated Income FY24, the Summary Budget FY24 chain -- is figure-for-figure '
        'identical to the "FY23 PEG ACCESS BUDGET" and "Work" sheets of that xlsx, which is '
        'the richer, unambiguous source; the pptm\'s own dense multi-column PEG ACCESS '
        'table is not reliably column-matchable from its flattened text per rule 13b)',
    'budget-workbooks/finance-committee/fy25-budget/dpw/fy25-dpw-budget-presentation.pptx':
        'figures are pictures -- same pattern as the FY24 DPW deck; the budget-category '
        'slides ("Fiscal Year 2025 DPW Budget Request", "General Highway", "Highway '
        'Labor", "Snow Removal", "Traffic Items", "Vehicle Maintenance", "Cemetery '
        'Department", "Tree Removal") show <p:pic> True / <a:tbl> False, extracted text '
        'is title-only',
    'budget-workbooks/finance-committee/fy25-budget/fy-2025-budget-calendar.pdf':
        'narrative not tabular -- a day/date/activity calendar of budget-process '
        'milestones (Select Board votes, warrant deadlines, Town Meeting date); no dollar '
        'figures or numeric table of any kind anywhere in the document',

    # --- batch 2 ---
    'budget-workbooks/finance-committee/fy25-budget/lunenburg-finance-committee-annual-report-for-fy25-4-11-24.docx':
        'narrative not tabular -- debt/capital-plan/SAP/40S prose; the one numeric pattern '
        '("a 16.39% reduction... from $3,516,182.23 to $2,939,956.12") is a single sentence, '
        'not a repeated row/column structure',
    'budget-workbooks/finance-committee/fy25-budget/lunenburg-finance-committee-annual-report-for-fy25.docx':
        'narrative not tabular -- an earlier/shorter draft of the "-4-11-24" annual report '
        '(same free-cash and debt figures in its first four paragraphs, then truncated); no '
        'total row or identity in either version',
    'budget-workbooks/finance-committee/fy25-budget/sewer/fy25-budget-presentation-for-fincom.pptx':
        'duplicate of budget-workbooks/finance-committee/fy25-budget/sewer/'
        'revised-sewer-powerpoint-fy25.pdf (identical Equipment Upgrades GRAND TOTAL '
        '$368,749.00, Revenue $1,751,189.00 and Expense $2,114,689.00 figures -- this is the '
        'same deck pre-revision)',
    'budget-workbooks/finance-committee/fy25-budget/school/nb-discussion-f-cip-update-3-6-24-update-1-.doc.pdf':
        'no printed total -- individual capital-project costs ($50,000 turf study, $160,000 '
        'doors, $131,000 security, etc.), no sum line anywhere',
    'budget-workbooks/finance-committee/fy25-budget/school/nb-discussion-f-district-building-update-3-6-24.doc.pdf':
        'no printed total -- per-item repair costs by building, no building subtotal or '
        'district total printed',
    'budget-workbooks/finance-committee/fy26-budget/annual-report/lunenburg-finance-committee-annual-report-for-fy26.docx':
        'no printed total -- "Table 1, Chapter 70 Funding FY13-FY26" is a 14-year time '
        'series with %-change columns (year-over-year growth, not additive) and no total '
        'row or 3-item identity; "Table 2" is referenced by caption only, no data follows it '
        'in the extracted text',
    'budget-workbooks/finance-committee/fy26-budget/annual-report/updated-lunenburg-finance-committee-annual-report-for-fy26.docx':
        'no printed total -- carries the identical Chapter 70 time-series Table 1 as '
        'lunenburg-finance-committee-annual-report-for-fy26.docx; same reasoning, a series '
        'with no sum or identity to tie',
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/fy26-land-use-budget-presentation.pptx':
        'no printed total -- four division budgets (Planning, Conservation, Building, ZBA) '
        'by FY25/FY26, no department total or sum line anywhere in the deck',
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/fy26-sewer-budget-presentation.pptx':
        'figures are pictures -- extracted text is bare slide titles ("ESTIMATED REVENUES", '
        '"ESTIMATED EXPENSES", "BUDGET SUMMARY") with no figures; slides 7-10 (the data '
        'slides) each show <p:pic> True / <a:tbl> False in the pptx XML',

    # --- batch 3 ---
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/lunenburg-public-schools/'
    'school-budget-files-amanda-moore-foia-request-to-school-dept/cafeteria-contract-signed-7-1-23-to-6-30-26.pdf':
        'no printed total -- a collective-bargaining agreement; its only table is the '
        '"Schedule A Food Service Salary Schedule" (hourly step rates by year), no sum or '
        'total line',
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/lunenburg-public-schools/'
    'school-budget-files-amanda-moore-foia-request-to-school-dept/lea-signed-moa-11-12-24.pdf':
        'narrative not tabular -- a Memorandum of Agreement amending the LEA contract; dollar '
        'figures appear only inside prose paragraphs ("Add $1,900.00 to Step 13..."), never '
        'in a row/column table',
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/lunenburg-public-schools/'
    'school-budget-files-amanda-moore-foia-request-to-school-dept/para-contract-24-25.pdf':
        'no printed total -- the Paraprofessional Union contract\'s only numeric tables are '
        'a longevity schedule and Appendix A step/salary schedules by year; none has a '
        'printed sum, total, or identity',
    'budget-workbooks/finance-committee/fy26-budget/department-presentations/lunenburg-public-schools/tmbudget03062025.pdf':
        'narrative not tabular -- a bullet-point comparison of three budget versions '
        '(Town Manager\'s Target, Needs Based, Level Service Adjusted); figures are standalone '
        'bullets with growth-rate percentages, no row/column table and nothing additive',
    'budget-workbooks/finance-committee/fy27-budget/budget-impact-statements/fire-fy-27-no-override-budget-notes-updated-31826.doc':
        'narrative not tabular -- repeated "Line- / Reduction- / IMPACT-" paragraphs, each '
        'with a single reduction figure explained in prose; no before/after pair and no '
        'printed total (this likely overlaps in substance with the Fire Department Operations '
        'table already extracted from the FY27 annual report, but here the reductions are '
        'embedded in narrative with no FY2026 Budget / Balanced Budget columns to tie against)',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/dpw-and-sewer/fy27-budget-presentation-dpw.pptx':
        'figures are pictures -- no slide in the deck contains <a:tbl>; the Trees, General '
        'Highway, Garage Supplies, Highway Salaries, Snow and Ice, Traffic Signs, Vehicle '
        'Maintenance, Cemetery, Recycling, Trash (PAYT) and Chapter 90 slides are bare titles '
        'with <p:pic> True and no numeric body text extracted',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/cherry-road.pdf':
        'narrative not tabular -- a Master Services Agreement order form for email archiving; '
        'its only "table" is a single degenerate line item (Qty 1, $1,500.00) where price, '
        'line total, annual total and form total are all the same number -- not a '
        'reconciling multi-line table',

    # --- batch 4 ---
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/it-department/'
    'presentation-budget-presentation-it-preliminary-final.pptx':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/department-presentations/'
        'it-department/presentation-budget-presentation-it-preliminary-final-2.26.26.pptx '
        '(identical Total IT figures across every FY column, including the $535,459.33 FY27 '
        'Requested total; same deck, filename missing the date suffix)',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/library/fy27-budget-presentation-library-fincomm.pptx':
        'figures are pictures -- the deck\'s only numeric content in extractable text is a '
        'handful of headline dollar figures with no line-item breakdown; the "Library Budget '
        'History" slide (slide8.xml) is a native chart object (chart:True, pic:False, '
        'tbl:False), not a table',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/pacc/'
    'pac-fy27-budget-presentation-march-5-2026-rev-2.pptx':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/department-presentations/'
        'pacc/fy27-budget-worksheets-pacc-fy26-fy27-comparison.redacted.xlsx (and also '
        'duplicates the sibling fy27-budget-worksheets-pacc-fy26-fy27-comparison-contingency-'
        'rev2.redacted.xlsx) -- this pptx presents the identical "190 PEG ACCESS COMMITTEE" '
        'table twice in slide form, line item for line item, matching both xlsx workbooks '
        'exactly (the plain $297,506.41 budget and the $306,206.41 contingency budget)',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/preliminary-budget-presentation-2.19.26/'
    'preliminary-budget-presentation-2.19.26-final.pdf':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/department-presentations/'
        'preliminary-budget-presentation-2.19.26/preliminary-budget-presentation-2.19.26-final-'
        'v.2.27.26.pptx (identical "FY 2027 Local Receipts Estimate" table, same figures '
        'line-for-line, same $3,360,524.00 total)',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/preliminary-budget-presentation-2.19.26/'
    'preliminary-budget-presentation-2.19.26-final.pptx':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/department-presentations/'
        'preliminary-budget-presentation-2.19.26/preliminary-budget-presentation-2.19.26-final-'
        'v.2.27.26.pptx (identical "FY 2027 Local Receipts Estimate" table and $3,360,524.00 '
        'total; only differs from that sibling by an immaterial typo elsewhere in the deck)',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/school-department/fy2027-school-department-q-and-a.docx':
        'narrative not tabular -- a Department/Question/Answer document plus a line-item list '
        '(Postage $6,000.00, Mileage $1,500.00, etc.) with no total row or identity anywhere',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/school-department/fincom-questions-2.26.26.docx':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/department-presentations/'
        'school-department/fy2027-school-department-q-and-a.docx (near-identical Q&A content '
        'and the identical "Description/FY27 Proposed" line-item list, e.g. Postage $6,000.00, '
        'H.S. Principal/Asst. Prin. $356,461.00 -- just reordered, with minor wording '
        'differences; that document is itself narrative not tabular, so this is a duplicate '
        'of a narrative document, not of an extracted table)',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/school-department/school-department-balanced-and-override-budgets.pdf':
        'no printed total -- discrete budget-impact line items (EL Teacher District $106,537, '
        'Special Educator $106,357, Assistant Business Manager $10,000, etc.), no slide states '
        'a grand total for additions, cuts, or net effect that these sum to',
    'budget-workbooks/finance-committee/fy27-budget/department-presentations/unclassified/'
    'draft-fy-27-general-govrernment-unclassified-budget-presentation-insurances-workers-comp-'
    'fica-budget-presentation-3.12.26-9b1f94e0.pptx':
        'duplicate of budget-workbooks/finance-committee/fy27-budget/department-presentations/'
        'unclassified/draft-fy-27-general-govrernment-unclassified-budget-presentation-'
        'insurances-workers-comp-fica-budget-presentation-3.12.26.pptx (every dollar figure in '
        'the reconciling table is identical -- Liability $230,000/Workers Comp $135,000/Group '
        'Health $3,695,424.59/Life $20,000/Unemployment $10,000/Medicare $410,000 = Total '
        '$4,500,424.59 in both files; this "-9b1f94e0" copy differs only in cosmetic wording '
        'and 8 extra lines of appended narrative)',
    'budget-workbooks/finance-committee/fy27-budget/fy27-budget-updates-special-town-meeting/calendar/'
    'draft-schedule-for-11-17-26-stm.pdf':
        'narrative not tabular -- a proposed meeting-schedule calendar (Day/Date/Proposed '
        'Activity), no financial figures anywhere',
    'budget-workbooks/finance-committee/fy27-budget/stormwater-task-force/storm-water-utility-budget-presentation-1.pptx':
        'figures are pictures -- 7 slides (New/Existing Personnel, Indirect Costs, Expenses '
        'x3, Vendors x2) show <p:pic> True / <a:tbl> False in the pptx XML; these are exactly '
        'the cost-breakdown slides whose figures would need to reconcile to the stated '
        '$496,793 budget, and the text-extractable prose figures sum to only $345,090 because '
        'the personnel-cost figures making up the difference are embedded as images',

    # --- batch 5 ---
    'budget-workbooks/finance-committee/fy27-budget/triboard-material/nabh-2024-annual-report.pdf':
        'narrative not tabular -- Nashoba Associated Boards of Health\'s OWN 2024 annual '
        'report (a different organization from Lunenburg\'s Finance Committee, serving 16 '
        'towns); all 11 pages checked via ===PAGE N=== markers -- prose, staff lists, and '
        'bar/pie chart graphics rendered as scattered percentages and axis labels with no '
        'row/column table and no raw counts to reconcile against any stated total',
}


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
    n_docs = len({t['document'] for t in EXTRACTED_TABLES})
    print(f'Extracted {len(EXTRACTED_TABLES)} table cells from {n_docs} documents -> {OUT_TABLES}')
