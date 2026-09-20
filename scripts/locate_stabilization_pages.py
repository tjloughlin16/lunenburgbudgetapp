#!/usr/bin/env python3
"""Which page of each annual report carries the stabilization funds, found by reading it.

    python3 scripts/locate_stabilization_pages.py    # rewrite sources/data/stabilization-pages.json

BY CONTENT, NOT BY ARITHMETIC. `extraction-plan.csv` records PRINTED page numbers and the
offset to the PDF index differs by year and is written down for none of them. Guessing it
put the search window six pages past FY2016's table and found nothing in fourteen of
fifteen reports.

AND IT USES THE EXTRACTOR'S OWN READER, which the first version of this did not. FY2014's
pages are a quarter turn with right-to-left characters, so the word STABILIZATION appears
in neither `extract_text()` nor the raw character order -- it is only there once the page
is reconstructed. Searching the raw order missed the one page that had already been proven
to parse, which is a good demonstration of why the locator and the reader must agree.
"""
import json
import os
import re
import sys
import warnings

warnings.filterwarnings('ignore')
import pdfplumber  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_stabilization import rows_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
OUT = os.path.join(ROOT, 'sources', 'data', 'stabilization-pages.json')


def main():
    out = {}
    for fy in range(2011, 2026):
        f = [x for x in os.listdir(DOCS)
             if re.search(r'fy-%d-annual-town-report\.pdf$' % fy, x)]
        if not f:
            continue
        hits = []
        try:
            with pdfplumber.open(os.path.join(DOCS, f[0])) as pdf:
                for i, p in enumerate(pdf.pages):
                    try:
                        lines = rows_of(p)
                    except Exception:
                        continue
                    if any('STABILIZATION' in l.upper() for l in lines):
                        hits.append(i)
        except Exception as e:
            print('FY%d: could not open — %s' % (fy, e), flush=True)
            continue
        out[str(fy)] = hits
        print('FY%d  %s' % (fy, hits), flush=True)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s' % os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
