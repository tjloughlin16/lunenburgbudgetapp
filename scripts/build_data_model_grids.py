#!/usr/bin/env python3
"""Regenerate the completeness grids inside notes/data-model/*.html from the database.

Those pages were built by hand, and hand-built copies of a computed thing go stale
silently. Both of them stated the coverage matrix as it stood on 3 September 2026, and by
the next morning the reader had been fixed, eleven more documents had been read and four
`missing` cells had become `obtained` -- so the pages said the archive lacked years it
holds, which is the exact error the whole coverage rewrite was about, sitting one directory
away from the fix.

So the grids are generated now. The prose around them is not: these are working pages with
an argument in them, and an argument is not a derived thing. Only the `<td>` cells of rows
whose label matches a row in the coverage matrix are rewritten, and any row the pages have
invented -- `Account Detail, transaction level  <- proposed` -- is left exactly as it is.

    python3 scripts/build_data_model_grids.py
    python3 scripts/build_data_model_grids.py --check     # fail if a page is stale

Only the FIRST grid on a page is generated. `after-request.html` also carries a projection
of what the two records requests would fill, and that is an argument rather than a derived
thing -- nothing here touches it.

`match-matrix.html` also marks whether a cell's document arrived as a spreadsheet or as a
PDF, which the coverage matrix itself does not yet record. That flag is derived here from
the file extensions of the documents behind the cell, because it is the whole point of
that page: only the spreadsheet carries the account code, and a PDF of the same report
cannot be joined to anything.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'fy28', 'public', 'data', 'ledger.json')
PAGES = [os.path.join(ROOT, 'notes', 'data-model', f)
         for f in ('match-matrix.html', 'after-request.html')]

# The glyph is never the only signal -- every cell also carries its state in the title
# attribute, which is what a screen reader and a text search both see.
GLYPH = {'obtained': '●', 'partial': '◐', 'missing': '·', 'unread': '▨'}
SHEET = ('.xlsx', '.xls', '.csv')

GRID = '<table class="cov">'
ROW_RE = re.compile(r'(<th scope="row">)(.*?)(</th>)(.*?)(</tr>)', re.S)
TOT_RE = re.compile(r'<td class="tot">.*?</td>', re.S)


def cells_for(cov, label, want_format):
    """The <td> run for one row of the grid, plus its `have` total."""
    rd = next((r for r in cov['rowDefs'] if r['label'] == label), None)
    if rd is None:
        return None
    out, have = [], 0
    for fy in cov['years']:
        cell = cov['cells'][str(fy)].get(rd['id']) or {'state': 'missing'}
        state = cell['state']
        if state == 'obtained':
            have += 1
        cls, title, glyph = state, state, GLYPH[state]
        if want_format and state == 'obtained':
            paths = [d.get('path') or '' for d in cell.get('documents', [])]
            if any(p.lower().endswith(SHEET) for p in paths):
                cls, title, glyph = state + ' f-sheet', 'obtained, spreadsheet', '●'
            elif paths:
                cls, title, glyph = state + ' f-pdf', 'obtained, PDF', '◍'
        out.append('<td class="s %s" title="FY%d — %s">%s</td>' % (cls, fy, title, glyph))
    out.append('<td class="tot">%d<span>/%d</span></td>' % (have, len(cov['years'])))
    return ''.join(out)


UNREAD_CSS = """
  /* Held, and not read. A different fact from `not held`, and the opposite action:
     nothing to ask anybody for, the document is already in the archive. */
  td.s.unread{color:var(--recover);background:var(--recover-soft)}"""


def rebuild(path, cov):
    src = open(path, encoding='utf-8').read()
    want_format = 'f-sheet' in src
    changed = [0]

    def one(m):
        open_th, label, close_th, body, close_tr = m.groups()
        # Only rows the page took from the coverage matrix. A row the page invented --
        # `Account Detail, transaction level  <- proposed` -- has no match and is left be.
        cells = cells_for(cov, label.split('  ⟵')[0].strip(), want_format)
        if cells is None or '<td class="s ' not in body:
            return m.group(0)
        if TOT_RE.search(body) is None:
            cells = TOT_RE.sub('', cells)
        if body.strip() != cells:
            changed[0] += 1
        return open_th + label + close_th + cells + close_tr

    # ONLY THE FIRST COVERAGE GRID. `after-request.html` carries three: what is held
    # today, what both requests would fill, and what neither asks for. The second is a
    # PROJECTION -- the argument of the page -- and is not derived from the database at
    # all. A first version rewrote every row it could match and quietly replaced twelve
    # cells of that projection with today's state, which is the same class of error as a
    # stale grid arriving from the other direction.
    #
    # And it has to be the first grid OF THAT CLASS, not the first table on the page:
    # `match-matrix.html` opens with two small tables of its own, so partitioning on the
    # first `</table>` put its coverage grid in the untouched half and the script reported
    # success having changed nothing.
    start = src.find(GRID)
    if start < 0:
        return src, 0
    end = src.find('</table>', start)
    out = src[:start] + ROW_RE.sub(one, src[start:end]) + src[end:]
    if 'td.s.unread' not in out:
        out = out.replace('  td.s.missing', UNREAD_CSS.strip('\n') + '\n  td.s.missing', 1)
    return out, changed[0]


def main():
    check = '--check' in sys.argv
    if not os.path.exists(LEDGER):
        print('no %s -- run scripts/export_ledger.py first' % LEDGER)
        return 1
    cov = json.load(open(LEDGER, encoding='utf-8'))['coverage']
    stale = 0
    for path in PAGES:
        if not os.path.exists(path):
            print('  missing %s' % os.path.relpath(path, ROOT))
            continue
        out, changed = rebuild(path, cov)
        same = out == open(path, encoding='utf-8').read()
        name = os.path.relpath(path, ROOT)
        if check:
            print('  %s  %s' % ('OK   ' if same else 'STALE', name))
            stale += 0 if same else 1
        else:
            if not same:
                open(path, 'w', encoding='utf-8').write(out)
            print('  %-42s %d row(s) rewritten' % (name, changed))
    if check and stale:
        print('\n%d page(s) stale. Run: python3 scripts/build_data_model_grids.py' % stale)
        return 1
    if check:
        print('\nboth grids match the coverage matrix')
    return 0


if __name__ == '__main__':
    sys.exit(main())
