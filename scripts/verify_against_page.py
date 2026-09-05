#!/usr/bin/env python3
"""Prepare a verification packet: the page as an image, beside what we extracted from it.

**This is the only verification most of this data can have, and it is the strongest one
available.** The annual town reports are the official record — approved by the Town Manager
and the Finance Committee, carrying tables exported from MUNIS. They are not a proxy for
something else and there is nothing more authoritative to check them against. So the
question is never "is the town's figure right"; it is only ever **"did we capture the
town's figure faithfully"**.

Most of these tables print no total, so no arithmetic can answer that. Rendering the page
and reading it can. Rule 13 in its plainest form: check what a reader sees, not only what
the file holds.

For each page it writes:

    <out>/<dataset>-<edition>-p<page>.png    the page, rendered upright
    <out>/<dataset>-<edition>-p<page>.md     every row we extracted from it

A reader — human or model — compares the two and reports what is on the page and not in
the extract, what is in the extract and not on the page, and any figure that differs.

Doing this found, on one page of one year: a whole row missing (`PL 94-142 #240`, the
federal special education grant, dropped because the label test wanted three consecutive
letters), a cell missing (`$29.075.55`, a thousands comma OCR'd as a point), and an empty
`group` column across all 2,246 rows. None of those shifted anything, so nothing arithmetic
could have noticed.

    python3 scripts/verify_against_page.py <dataset> <edition> [--pages 31,32] [--out DIR]
"""

import argparse
import collections
import csv
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
DOCS = os.path.join(ROOT, 'sources', 'town-budget', 'docs')
RENDER = os.path.join(ROOT, 'scripts', 'render_page.swift')

FILES = {
    'special_revenue': 'special-revenue-funds.csv',
    'receipts': 'annual-report-receipts.csv',
    'rosters': 'staff-roster-entries.csv',
}


def dataset_file(name):
    if name in FILES:
        return os.path.join(DATA, FILES[name])
    return os.path.join(DATA, f'report-{name.replace("_", "-")}.csv')


def pdf_for(edition):
    import glob, re
    year = re.search(r'(\d{4})', edition).group(1)
    for p in sorted(glob.glob(os.path.join(DOCS, f'*fy-{year}-annual-town-report*.pdf'))):
        if ('addendum' in p) == ('addendum' in edition):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset')
    ap.add_argument('edition')
    ap.add_argument('--pages')
    ap.add_argument('--out', default=os.path.join(ROOT, 'sources', 'data', 'verify'))
    ap.add_argument('--scale', default='3.0')
    args = ap.parse_args()

    path = dataset_file(args.dataset)
    if not os.path.exists(path):
        print(f'no such dataset file: {path}')
        return 2
    rows = [r for r in csv.DictReader(open(path))
            if (r.get('edition') or f"FY{r.get('fy','')}") == args.edition]
    if not rows:
        print(f'{args.dataset}: nothing for {args.edition}')
        return 2

    want = ([int(p) for p in args.pages.split(',')] if args.pages
            else sorted({int(r['page']) for r in rows if str(r.get('page','')).isdigit()}))
    pdf = pdf_for(args.edition)
    os.makedirs(args.out, exist_ok=True)

    by_page = collections.defaultdict(list)
    for r in rows:
        if str(r.get('page', '')).isdigit():
            by_page[int(r['page'])].append(r)

    made = []
    for page in want:
        stem = f'{args.dataset}-{args.edition}-p{page:03d}'
        png = os.path.join(args.out, stem + '.png')
        subprocess.run(['swift', RENDER, pdf, str(page), png, args.scale],
                       capture_output=True)
        mine = by_page.get(page, [])
        cols = [c for c in (rows[0].keys()) if c.startswith('v')]
        with open(os.path.join(args.out, stem + '.md'), 'w') as fh:
            fh.write(f'# {args.dataset} — {args.edition} page {page}\n\n')
            fh.write(f'{len(mine)} rows extracted. Compare against `{stem}.png`.\n\n')
            if mine and 'columns_as_printed' in mine[0]:
                fh.write(f"Columns as printed: `{mine[0]['columns_as_printed'][:200]}`\n\n")
            label = ('fund' if 'fund' in rows[0] else
                     'label' if 'label' in rows[0] else
                     'name' if 'name' in rows[0] else 'source')
            head = ['#', 'group' if 'group' in rows[0] else '', label] + cols
            head = [h for h in head if h]
            fh.write('| ' + ' | '.join(head) + ' |\n')
            fh.write('|' + '---|' * len(head) + '\n')
            for i, r in enumerate(mine, 1):
                cells = [str(i)]
                if 'group' in r:
                    cells.append(r.get('group', ''))
                cells.append(r.get(label, ''))
                cells += [r.get(c, '') or '' for c in cols]
                fh.write('| ' + ' | '.join(cells) + ' |\n')
            flags = [r for r in mine if r.get('unparsed_cells')
                     or (r.get('repaired_cells') or '0') not in ('0', '')]
            if flags:
                fh.write('\n## Cells this extraction repaired or could not parse\n\n')
                for r in flags:
                    fh.write(f"- `{r.get(label,'')}`: "
                             f"repaired={r.get('repaired_cells','0')} "
                             f"unparsed=`{r.get('unparsed_cells','')}`\n")
        made.append((stem, len(mine)))

    print(f'{len(made)} verification packets in {os.path.relpath(args.out, ROOT)}:')
    for stem, n in made:
        print(f'  {stem}  ({n} rows)')
    print('\nEach packet is a rendered page plus the rows extracted from it. '
          'Compare and report:\n'
          '  - rows ON THE PAGE but not in the extract\n'
          '  - rows in the extract but NOT on the page\n'
          '  - any figure that differs, cell by cell')


if __name__ == '__main__':
    sys.exit(main() or 0)
