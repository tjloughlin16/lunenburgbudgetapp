"""Every page somebody READ, checked against the total the page itself prints.

    python3 scripts/verify_page_reads.py
    python3 scripts/verify_page_reads.py --check

WHY A PAGE IS READ RATHER THAN RECOGNISED

TJ, 28 September 2026: *"i'm 100% done with OCR. that's totally a waste of my time and
credits"* and *"you spend more time in model costs rebuilding and rebuilding and rebuilding
off of broken ocr."*

He is right and the measurement is not close. FY2024's special revenue schedule, four pages,
164 fund rows:

    recognition   14 of 60 rows on page 25, and DIFFERENT DIGITS for the same row at
                  different resolutions -- 90.61 and 0.61, 94.65 and 4.65 -- so merging the
                  passes could not help. An afternoon of machinery built around that.
    read          164 of 164 rows, and all six columns tie to the printed total, first try,
                  in about ten minutes.

The same thing happened on the trust listing that morning: recognition held 30 accounts
where the page prints 40, and two of the missing ones were about to be written up as a
disagreement in the town's books.

WHAT MAKES A READ SAFE -- AND IT IS NOT THE READER

The arithmetic. A person or a model reading a page is a READING like any other, and rule 13a
is explicit that something a person assembled is an argument rather than a record. What
settles it is that 164 rows land on six totals the town printed and we did not use: 83.86,
83.86, 4,963,068.15, 116,241.96, 0.00 and (719,886.84). A single wrong digit anywhere breaks
all of them.

So this script is the point of the whole approach. The reading happens ONCE, by eye, and is
committed as data in `sources/data/page-reads/` with the document, the page and who read it.
This re-proves it on every run, for ever, which is the property recognition had and a read
does not.

A PAGE THAT PRINTS NO TOTAL CANNOT BE CHECKED THIS WAY, and that is a property of the page
rather than of the reader -- recognition had exactly the same limit. Such a page needs a
coverage check (every figure printed is captured) or a second printing of the same quantity
elsewhere in the document. Say which, in the transcription's `proof` column.
"""
import argparse
import collections
import csv
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READS = os.path.join(ROOT, 'sources', 'data', 'page-reads')

# THE TOTAL IS READ OFF THE PAGE TOO, and lives in the transcription as `kind=total` --
# not typed in here. Rule 2: a figure in prose or in code is the one thing that can be
# silently wrong, and a check whose expected value is hardcoded stops being a check the day
# somebody corrects the data.
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.parse_args()

    got = collections.defaultdict(lambda: collections.defaultdict(float))
    want = collections.defaultdict(dict)
    printed_on = {}
    rows = collections.Counter()
    pages = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(READS, '*.csv'))):
        name = os.path.basename(f)
        key = (name.split('-')[0][2:], '-'.join(name.split('-')[2:]).replace('.csv', ''))
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if not (r.get('value') or '').strip():
                continue
            if (r.get('kind') or 'fund') == 'total':
                want[key][r['column']] = float(r['value'])
                printed_on[key] = 'page %s, the row `%s`' % (r['page'], r['fund_name'])
                continue
            got[key][r['column']] += float(r['value'])
            rows[key] += 1
            pages[key].add(r['page'])

    bad = []
    for key in sorted(got):
        if key not in want:
            print('FY%s %s -- %d rows across %d pages, NO PRINTED TOTAL: the transcription '
                  'must say in `proof` what checks it' % (key[0], key[1], rows[key],
                                                          len(pages[key])))
            continue
        print('FY%s %s -- %d rows across %d pages, against %s'
              % (key[0], key[1], rows[key], len(pages[key]), printed_on[key]))
        for col, printed in sorted(want[key].items()):
            g = round(got[key].get(col, 0.0), 2)
            ok = abs(g - printed) <= 0.02
            print('    %-22s %16s   printed %16s   %s'
                  % (col, format(g, ','), format(printed, ','),
                     'ties' if ok else 'OFF BY %s' % format(round(g - printed, 2), ',')))
            if not ok:
                bad.append('FY%s %s %s: %s against a printed %s'
                           % (key[0], key[1], col, format(g, ','), format(printed, ',')))

    if bad:
        print('\n%d transcribed column(s) do not tie:\n  %s'
              % (len(bad), '\n  '.join(bad)), file=sys.stderr)
        return 1
    print('\nevery transcribed page ties to the total its own document prints')
    return 0


if __name__ == '__main__':
    sys.exit(main())
