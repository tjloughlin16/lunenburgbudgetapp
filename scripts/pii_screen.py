#!/usr/bin/env python3
"""Does this document hold data about identifiable people? A screen, not a verdict.

    import pii_screen
    findings = pii_screen.screen(name, blob)   # [] means nothing found, NOT "clean"

    python3 scripts/pii_screen.py FILE...       # print what it finds

WHY. TJ, 4 October 2026, after a records-request delivery put one employee's number,
name, start date, grade and salary into the PUBLIC bucket, which cannot delete it for ten
years: *"i think we probably need a REDACTION mechanism, so that we can have a private
storage of the raw, and a public version with all redacted PII removed. This will come up
in MUNIS data too."* The keyword pass that had been run saw the word `salary` in that
workbook's header and nobody looked at the sheet underneath.

WHAT IT LOOKS FOR, and it is deliberately STRUCTURAL:

  * a spreadsheet header that makes a table PER PERSON -- a name column, an employee
    number, a date of birth or hire, a plan tier, a leave balance. A line-item budget
    with a `SALARY LAND USE DIRECTOR` row is a budget by POSITION, which the town
    publishes itself, and is not flagged.
  * identifier PATTERNS anywhere in the text: a social security number, a date of birth,
    a personal email address, and medical or leave terms (FMLA, medical leave).

WHAT IT CANNOT SEE, said here so nobody reads `[]` as a clearance. A name in running prose
-- "the officer out on leave is Smith" -- has no structure to find, and nothing in this
repository can recognise a person's name. The screen catches the TABLES and the PATTERNS.

AND IT FAILS CLOSED. A document it cannot read in full -- a scan, a digital PDF with even
one picture-only page, a pre-2007 PowerPoint, an image -- returns an `unscreenable` finding
rather than nothing,
because "found nothing" and "could not look" are different statements (CLAUDE.md, 13c).
"""
import io
import re
import sys
import zipfile

# A header cell that makes a table about PEOPLE rather than positions. Matched against the
# whole cell, trimmed, so `Last` is a name column and `Last year` is not.
PERSON_HEADERS = re.compile(
    r'^(last|first|last name|first name|lname|fname|surname|employee|employee name|'
    r'employee ?(no|#|number|id)|emp ?(no|#|id)\.?|name|full name|'
    r'dob|date of birth|birth ?date|ssn|social security( no| number)?|'
    r'hire date|date of hire|start dt|start date|service date|permanent date|'
    r'home address|street address|address|home phone|cell|personal email|'
    r'fam/ind|coverage|coverage tier|plan tier|dependents?|'
    r'vaca(tion)? hours|sick hours|leave balance|accrued (vacation|sick))$', re.I)
# One header alone can be innocent (`Name` heads a list of funds). A per-person table
# carries a NAME column and something about that person, so a sheet is flagged when it
# shows at least two of these in one row -- or any one of the unambiguous ones.
UNAMBIGUOUS = re.compile(
    r'^(last name|first name|employee name|employee ?(no|#|number|id)|emp ?(no|#|id)\.?|'
    r'dob|date of birth|birth ?date|ssn|social security.*|home address|fam/ind|'
    r'vaca(tion)? hours|sick hours|leave balance)$', re.I)

PATTERNS = [
    ('a social security number', re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
    ('a date of birth', re.compile(r'\b(date of birth|d\.o\.b\.?|DOB)\b', re.I)),
    ('a personal email address', re.compile(
        r'\b[\w.+-]+@(gmail|yahoo|hotmail|outlook|aol|comcast|verizon|icloud|me|msn|'
        r'live|charter)\.(com|net)\b', re.I)),
    ('a medical or leave term', re.compile(
        r'\b(FMLA|medical leave|disability leave|workers\W? comp(ensation)? claim|'
        r'diagnos(is|ed))\b', re.I)),
]

# A PER-PERSON TABLE, FOUND IN TEXT RATHER THAN IN CELLS. A scanned staff list has no
# cells: OCR gives lines, and a page read sideways -- about 700 of the annual reports'
# 2,751 were, with every word spelled right (`check_ocr_orientation.py`) -- collapses a
# table into one line of labels and one of values. Phrases survive that; geometry does not.
# So: two or more DISTINCT phrases from this list on one page is a table about people.
TABLE_PHRASES = re.compile(
    r'\b(last name|first name|employee name|employee (?:no|#|number|id)|emp\.? ?(?:no|#)|'
    r'hire date|date of hire|start date|date of birth|birth ?date|social security|'
    r'home address|vacation hours|sick (?:hours|balance)|leave balance|fam/ind)\b', re.I)


def normalise(text):
    """Undo the confusions OCR is known to make here, before any pattern is tried.

    From the annual reports: `$` read as `S`, a comma read as a full stop (13b, 13c), and
    the usual O/0 and l/1 swaps. Applied only BETWEEN DIGITS, so words are untouched: an SSN
    read as `l23.45-6789` must still match.
    """
    t = re.sub(r'(?<=\d)[Oo](?=\d)|(?<=\d)[Oo]\b|\b[Oo](?=\d)', '0', text)
    t = re.sub(r'(?<=\d)[lI|](?=\d)|\b[lI|](?=\d{2})', '1', t)
    t = re.sub(r'(?<=\d)\s?[.\u2013\u2014_~]\s?(?=\d)', '-', t)
    return t


def screen_text(text, out, page_marker=r'===PAGE (\d+)==='):
    """Patterns and table phrases over TEXT -- a PDF, a Word file, slides, or OCR.

    Every line is ALSO tried reversed: the FY2016 annual report's text layer is born-digital
    and MIRRORED -- `SEXAT` for `TAXES` -- and no pattern matches a reversed string.
    """
    variants = normalise(text)
    variants += '\n' + '\n'.join(line[::-1] for line in variants.splitlines())
    for what, pat in PATTERNS:
        n = len(pat.findall(variants))
        if n:
            out.append(f'{n} match(es) for {what}')
    pages = re.split(page_marker, text)
    # re.split with a group gives [pre, n1, body1, n2, body2, ...]
    chunks = [('', pages[0])] + list(zip(pages[1::2], pages[2::2]))
    for num, body in chunks:
        both = body + '\n' + '\n'.join(l[::-1] for l in body.splitlines())
        found = {m.lower() for m in TABLE_PHRASES.findall(both)}
        if len(found) >= 2:
            where = f'page {num}' if num else 'the text'
            out.append(f'{where}: looks like a per-person table '
                       f'({", ".join(sorted(found)[:5])})')
    return out


MIN_TEXT = 200   # OCR that returns less than this is not a reading (redact.py --review). NOT a scan test: see pdf_kind.py


def _cell_text(v):
    return str(v).strip() if v is not None else ''


def _sheets(blob):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    for ws in wb.worksheets:
        yield ws.title, ws.iter_rows(values_only=True)


def _xlsx(blob, out):
    text = []
    for title, rows in _sheets(blob):
        for i, row in enumerate(rows):
            cells = [_cell_text(v) for v in row]
            hits = [c for c in cells if c and PERSON_HEADERS.match(c)]
            if len(hits) >= 2 or any(UNAMBIGUOUS.match(c) for c in hits):
                out.append(f'sheet {title!r} row {i + 1}: a per-person table '
                           f'(headers {", ".join(repr(h) for h in hits[:6])})')
            text.extend(c for c in cells if c)
    return '\n'.join(text)


def _ooxml_text(blob, prefixes):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        parts = [n for n in z.namelist()
                 if n.endswith('.xml') and n.startswith(prefixes)]
        return '\n'.join(re.sub(r'<[^>]+>', ' ', z.read(n).decode('utf8', 'ignore'))
                         for n in parts)


def _pdf_text(blob):
    import pypdf
    import logging
    logging.getLogger('pypdf').setLevel(logging.CRITICAL)
    r = pypdf.PdfReader(io.BytesIO(blob))
    return '\n'.join((p.extract_text() or '') for p in r.pages)


def screen(name, blob):
    """A list of findings, each a sentence saying WHERE and WHAT -- never the value."""
    ext = name.lower().rsplit('.', 1)[-1]
    out = []
    try:
        if ext in ('xlsx', 'xlsm'):
            text = _xlsx(blob, out)
        elif ext in ('docx',):
            text = _ooxml_text(blob, ('word/',))
        elif ext in ('pptx', 'pptm'):
            text = _ooxml_text(blob, ('ppt/slides/', 'ppt/notesSlides/', 'ppt/comments'))
        elif ext == 'pdf':
            # Which pages can be READ is decided from what is on them (`pdf_kind`), never
            # from a character count: a digital deck with screenshot slides read as clean
            # under the count, and the screenshots were never looked at.
            import pdf_kind
            k = pdf_kind.classify(blob)
            text = k['text']
            blind = [p for p in k['pages'] if p['kind'] in pdf_kind.OCR_KINDS]
            if blind:
                return screen_text(text, [f'unscreenable: {len(blind)} of {len(k["pages"])} '
                                          f'page(s) hold no readable text '
                                          f'({pdf_kind.summary(k)})'])
        elif ext in ('csv', 'txt', 'md'):
            text = blob.decode('utf8', 'replace')
        else:
            return [f'unscreenable: no reader for .{ext}']
    except Exception as e:
        return [f'unscreenable: {type(e).__name__} reading it']
    return screen_text(text, out)


if __name__ == '__main__':
    for f in sys.argv[1:]:
        found = screen(f, open(f, 'rb').read())
        print(('FLAG  ' if found else 'none  ') + f)
        for x in found:
            print('      ' + x)
