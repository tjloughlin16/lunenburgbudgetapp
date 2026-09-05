#!/usr/bin/env python3
"""Every fault, oddity and trap found in the annual town reports, as data.

Reading sixteen reports end to end turned up 150 things the readers flagged as unexpected
and 815 tables carrying notes -- and all of it was locked inside
`sources/data/inventory/FY*.json`, where nothing can query it. This pulls it out.

**These are faults in the published documents, not in our reading of them**, and that is
why they are worth keeping. A few of the sharper ones:

  * FY2018's omnibus foots to $36,804,408.83 under a heading and an article vote that both
    say $36,867,903.83, with a third figure in the Town Manager's report.
  * FY2017 printed 2017 bond anticipation notes as $295,925 against its own balance
    sheet's $2,895,925, and FY2018 corrected it silently.
  * FY2020 prints an entire presidential primary twice, pages 189-191 and 193-195.
  * FY2016 prints a special revenue page twice, unheaded, and starts its employee list
    part-way through the alphabet at BENOIT.

Rule 8 governs what happens to these: a discrepancy goes in an analysis document and
reaches the app only when it changes an assumption. This file is the register, not an
accusation -- most of these are typesetting, and the useful ones are the handful that
change what a figure means.

    python3 scripts/build_report_anomalies.py
"""

import csv
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, 'sources', 'data', 'inventory')
OUT = os.path.join(ROOT, 'sources', 'data', 'report-anomalies.csv')

# What kind of problem a note describes. Ordered: the first match wins, so the more
# specific patterns come first.
KINDS = [
    ('does not sum',      r"do(?:es)?n'?t (?:add|sum)|fail(?:s)? to sum|does not tie|"
                          r"do not sum|doesn't tie|arithmetic"),
    ('two figures differ', r'contradict|differs? from|two different|three different|'
                          r'inconsistent|disagree'),
    ('duplicated',        r'\bduplicat|printed twice|identical to|byte-identical|reprint'),
    ('stale / copied forward', r'stale|carried forward unchanged|copy-forward|'
                          r'unchanged from|still ending at|not advanced'),
    ('announced but absent', r'never printed|not printed|absent|missing from|'
                          r'no table|nothing follows|promised'),
    ('unreadable / OCR damage', r'\bOCR\b|transpos|collapsed|shattered|reading order|'
                          r'no text layer|garbl|mangl|clipped|cut off|upside down'),
    ('no heading',        r'no heading|unheaded|no title|not in the (?:contents|ToC)|'
                          r'only the ToC'),
    ('page numbering',    r'printed page|page numbers run|folio|offset by'),
    ('continues elsewhere', r'continu|spills|carries on|second page'),
]


def classify(text):
    t = (text or '').lower()
    for kind, pat in KINDS:
        if re.search(pat, t, re.I):
            return kind
    return 'note'


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(INV, 'FY*.json'))):
        d = json.load(open(path))
        edition = os.path.basename(path).replace('.json', '')
        fy, doc = d.get('fy'), d.get('document', '')

        for s in d.get('surprises') or []:
            rows.append({'fy': fy, 'edition': edition, 'document': doc, 'pages': '',
                         'table': '', 'kind': classify(s), 'source': 'surprise',
                         'detail': re.sub(r'\s+', ' ', s).strip()})

        for t in d.get('tables', []):
            note = (t.get('notes') or '').strip()
            if not note:
                continue
            # Split a long note into sentences and keep the ones that describe a problem,
            # rather than the ones that describe the table. A note saying "columns are
            # right-aligned" is not an anomaly.
            for part in re.split(r'(?<=[.;])\s+(?=[A-Z])', note):
                if len(part) < 25:
                    continue
                kind = classify(part)
                if kind == 'note':
                    continue
                rows.append({'fy': fy, 'edition': edition, 'document': doc,
                             'pages': t.get('pages', ''), 'table': t.get('name', ''),
                             'kind': kind, 'source': 'table note',
                             'detail': re.sub(r'\s+', ' ', part).strip()})

    rows.sort(key=lambda r: (str(r['fy']), r['kind'], str(r['pages'])))
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'edition', 'document', 'pages', 'table',
                                           'kind', 'source', 'detail'])
        w.writeheader()
        w.writerows(rows)

    import collections
    by_kind = collections.Counter(r['kind'] for r in rows)
    by_year = collections.Counter(str(r['fy']) for r in rows)
    print(f'{len(rows)} anomalies from {len(glob.glob(os.path.join(INV, "FY*.json")))} '
          f'reports\n')
    print('by kind:')
    for k, n in by_kind.most_common():
        print(f'  {n:>4}  {k}')
    print('\nby year:')
    print('  ' + '  '.join(f'{y}:{n}' for y, n in sorted(by_year.items())))
    print(f'\nwrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
