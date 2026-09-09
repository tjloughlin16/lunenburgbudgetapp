#!/usr/bin/env python3
"""A streaming reader for the DESE open-data workbook exports, and the peer set.

WHY THIS EXISTS RATHER THAN `openpyxl.load_workbook(read_only=True)`

`dese-teachers-by-grade-subject.xlsx` is 133 MB and 1,774,971 rows. openpyxl's read-only
mode still builds a cell object per cell, and a first pass that used it to scan twelve of
these files did not finish in twenty minutes -- which matters, because these extracts run
under `check_generated.py` on every pass and a check nobody is willing to wait for is a
check that stops being run.

These exports are a single worksheet with no styling and no shared string table, so
essentially all of what openpyxl does for them is parse XML. `iterparse` over the sheet
part does that directly: the 553,582-row teacher file reads in 43 seconds this way, and
the whole set of twelve in a few minutes.

WHAT IT DOES NOT DO, DELIBERATELY

No dates, no formulas, no number formats, no merged cells, no second worksheet by name.
Every value comes back as the TEXT the file holds, and the caller converts. That is the
right default for rule 13: `'0.0'` and `''` are different things in these files and a
reader that silently made both `0.0` would erase the distinction before anybody saw it.

For anything with a front sheet, formulas or several sheets -- the two Chapter 70
workbooks -- use openpyxl. `extract_dese_state_aid.py` does.
"""
import csv
import os
import zipfile
from xml.etree.ElementTree import iterparse

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
RADAR = os.path.join(DATA, 'dese-radar.csv')

LUNENBURG = '01620000'
STATE = '00000000'


def peers():
    """Lunenburg and the COMPARISON districts, read from `dese-radar.csv`.

    Never typed. Three of the first eight DESE org codes written from memory in the radar
    extract were invented, and only a reconciliation caught them.

    NOT EVERY DISTRICT IN THAT FILE. `dese-radar.csv` also carries the DESTINATIONS -- the
    districts Lunenburg children leave for -- and those are a different set answering a
    different question. Reading the peer set back off whatever RADAR happened to write
    made a wider archive into a wider comparison set, silently, in four extracts at once:
    it would have put a regional vocational district and two charter schools into the
    six-district Chapter 70 standing table. So the roles are declared in
    extract_dese_radar.py and this filters on them.
    """
    from extract_dese_radar import PEERS
    seen = {}
    with open(RADAR, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] in PEERS:
                seen[r['lea']] = r['district']
    if LUNENBURG not in seen:
        raise SystemExit('dese-radar.csv does not carry Lunenburg; the peer set cannot be '
                         'derived from it. Nothing written.')
    missing = sorted(set(PEERS) - set(seen))
    if missing:
        raise SystemExit('dese-radar.csv is missing peer district(s) %s. A comparison set '
                         'that quietly shrank is the same defect as one that quietly grew. '
                         'Nothing written.' % missing)
    return seen


def _shared(z):
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    out, buf = [], []
    for _, el in iterparse(z.open('xl/sharedStrings.xml'), ('end',)):
        if el.tag == NS + 't':
            buf.append(el.text or '')
        elif el.tag == NS + 'si':
            out.append(''.join(buf))
            buf = []
            el.clear()
    return out


def _colnum(ref):
    n = 0
    for ch in ref:
        if ch.isdigit():
            break
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def raw_rows(path, sheet='xl/worksheets/sheet1.xml'):
    """Every row of the sheet, as a list of strings, positioned by cell reference.

    Positioned, not appended: these exports omit empty cells entirely, so reading them in
    document order would shift every value after the first blank one into the wrong
    column. `r="D7"` is the coordinate and it is what places the value.
    """
    z = zipfile.ZipFile(path)
    sst = _shared(z)
    cur = {}
    for _, el in iterparse(z.open(sheet), ('end',)):
        if el.tag == NS + 'c':
            t = el.get('t')
            v = el.find(NS + 'v')
            if t == 'inlineStr':
                is_ = el.find(NS + 'is')
                txt = ('' if is_ is None
                       else ''.join(x.text or '' for x in is_.iter(NS + 't')))
            elif t == 's':
                txt = sst[int(v.text)] if v is not None else ''
            else:
                txt = v.text if v is not None else ''
            if txt not in (None, ''):
                cur[_colnum(el.get('r') or '')] = txt
            el.clear()
        elif el.tag == NS + 'row':
            yield [cur.get(i, '') for i in range(max(cur) + 1)] if cur else []
            cur = {}
            el.clear()
    z.close()


def records(path, expect, doc):
    """Rows as dicts, with the header asserted against the columns we were told to expect.

    A column list is part of the finding (rule 13). If DESE republishes this dataset with
    a renamed or reordered column, every downstream figure would still compute and would
    silently be about something else -- so the header is compared in full and in order,
    and a mismatch stops the run.
    """
    g = raw_rows(path)
    head = [c.strip() for c in next(g)]
    if head != list(expect):
        raise SystemExit(
            '%s\n  columns are %s\n  expected     %s\nNothing written. A renamed column '
            'would recompute every figure here against a different quantity.'
            % (doc, head, list(expect)))
    n = len(head)
    for r in g:
        if not r or not r[0]:
            continue
        if len(r) < n:
            r = r + [''] * (n - len(r))
        yield dict(zip(head, [c.strip() for c in r[:n]]))


def num(v):
    """A figure, or None. Blank and DESE's suppression markers are NOT zero.

    DESE prints `N/A` where a measure does not apply and blanks where a count is
    suppressed for a small cell. Both are absent, and neither is nought -- a suppressed
    count read as 0 would understate every total it entered.
    """
    v = '' if v is None else str(v).strip().replace(',', '').replace('$', '')
    if v in ('', '-', '--', 'N/A', 'n/a', 'NA', '.'):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def fmt(v):
    """A number back to text, without turning an integer into `1.0`."""
    if v is None:
        return ''
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return str(v)
