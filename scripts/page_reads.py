#!/usr/bin/env python3
"""Read a `sources/data/page-reads/*.csv` transcription, un-abbreviating the sticky columns.

WHY THIS EXISTS. These files are one row per FIGURE read off a page, and four of their
columns are facts about the PAGE rather than about the figure: which document it is, who
read it, the tolerance declared, and the `proof` -- a paragraph stating the identity that
closed, the coordinate, and what the read does NOT establish.

A column gets a value on every row. So `fy2021-p162-gross-wages.csv` carried its 1,755
character proof 613 times, for 611 names: 98% of the file was one paragraph. Across 313
files that was 101.6 MB of tracked text for under 3 MB of figures, and it made the
archive unpushable -- `pages-read.csv`, which is derived from these, reached 114 MB and
GitHub refuses a blob over 100.

A fact about a group, stored at row grain. The same defect as a bare number in a stat
box: right content, wrong unit.

THE CONVENTION, and it is lossless. In a sticky column, A BLANK MEANS `the same as the
row above`. A value appears only where it CHANGES. That handles both the 273 files whose
proof is constant and the 40 where it varies -- an `attested` row states its own proof --
without anyone having to declare which kind a file is.

A genuinely empty cell stays empty, because forward-filling '' gives ''.

Every reader of these files must come through here. `fund_number`, `fund_name`, `kind`,
`column`, `value` and `page` are NEVER sticky: they are the figure.
"""

import csv
import sys

csv.field_size_limit(10 ** 9)

# Facts about the page, not about the figure.
# NOT `status`: `map_annual_report_pages.PROOF` reads it PER ROW out of the aggregate and
# does not forward-fill, so blanking it would un-prove every page in the archive.
STICKY = ('document', 'read_by', 'tolerance', 'proof', 'reconciliation')


def rows(path):
    """Every row, with blanks in the sticky columns filled from the row above."""
    with open(path, newline='', encoding='utf-8-sig') as fh:
        last = {}
        for r in csv.DictReader(fh):
            for c in STICKY:
                if c not in r:
                    continue
                if (r[c] or '') == '':
                    r[c] = last.get(c, '')
                else:
                    last[c] = r[c]
            yield r


def abbreviate(rs):
    """The inverse: blank a sticky cell that repeats the one above. Lossless by `rows()`."""
    out, last = [], {}
    for r in rs:
        r = dict(r)
        for c in STICKY:
            if c not in r:
                continue
            v = r[c] or ''
            if v == last.get(c, ''):
                r[c] = ''
            else:
                last[c] = v
        out.append(r)
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        rs = list(rows(p))
        print('%s: %d rows' % (p, len(rs)))
