#!/usr/bin/env python3
"""The two documents somebody arriving at the annual-report archive needs.

`notes/reference/ANNUAL-REPORTS.md` — what exists, where each thing lives, what state it is
in, and what is still uncaptured. The entry point, so none of this has to be rediscovered.

`notes/reference/BACKUP.md` — every path with its size and **how many copies of it exist**.
That last column is the point. A file on this machine and nowhere else is one disk failure
from gone, and the phrase "irreplaceable if the links die" hid that: six of the sixteen
annual town reports are too large to publish with the site and are not in git, so the
working tree is their only copy.

Both are GENERATED, because rule 2 applies to a document about the data as much as to one
about the town: a size or a row count typed into prose keeps rendering long after it stops
being true. The previous BACKUP.md said the mirror was 399 MB; it is 723 MB.

    python3 scripts/build_archive_guide.py [--check]
"""

import argparse
import collections
import csv
import glob
import os
import re
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'docs')
GUIDE = os.path.join(ROOT, 'notes', 'reference', 'ANNUAL-REPORTS.md')
BACKUP = os.path.join(ROOT, 'notes', 'reference', 'BACKUP.md')

# dataset -> (csv basename, what it is, how it is proved)
HAND = [
    ('placement-counts', 'Out-of-district placements, by year',
     'parts sum to the total; each year states its predecessor'),
    ('ballot-questions', 'What the town was asked to fund, and whether it agreed',
     'every tally against its own precinct figures'),
    ('annual-report-receipts', 'Town receipts by source',
     "ties to the report's printed GRAND TOTAL, twice over"),
    ('special-revenue-funds', 'The funds outside the general fund',
     'forward + receipts − disbursements = carried forward'),
    ('staff-roster-entries', 'Every name printed on a school staff roster',
     'every line of every page accounted for'),
    ('staff-roster-counts', 'Roster headcount by school and year', 'derived from the above'),
    ('staff-position-map', 'Roster position titles, grouped',
     'a hypothesis about which titles are the same job'),
]
ABOUT = [
    ('annual-report-catalogue', 'Every table in every report, with its PRINTED heading'),
    ('annual-report-contents', 'What each report contains, section by section'),
    ('annual-report-survey', 'Every page, and which instrument recovers it'),
    ('extraction-plan', 'Which pages each dataset is read from'),
    ('dataset-provenance', 'Every dataset joined to the document it came from'),
    ('report-anomalies', 'Where a reading is not credible, and where to look'),
]


def du(path):
    """(bytes, file count) for a directory or file."""
    if os.path.isfile(path):
        return os.path.getsize(path), 1
    total = n = 0
    for dirpath, _d, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                continue
            n += 1
    return total, n


def mb(n):
    return f'{n / 1e6:,.0f} MB' if n >= 1e6 else f'{n / 1e3:,.0f} KB'


def tracked_files():
    out = subprocess.run(['git', '-C', ROOT, 'ls-files'], capture_output=True, text=True)
    return set(out.stdout.split())


def stored_files():
    """Repo-relative paths that exist as objects in the R2 archive.

    Since 5 September 2026 the copies column has three places to count, not two, and the
    third is the only one not on this disk. The publishers' documents left git that day;
    saying "working tree only" about them would be false in the direction that stops
    somebody worrying about a file that is genuinely fine.

    **Read from what was uploaded, not from what was meant to be.** The manifest is a
    list of files that ought to be in the bucket; `archive-push-state.csv` records the
    ones `sync_archive.py` uploaded AND read back with a matching sha256. Counting the
    manifest here would be a document about how many copies exist quoting an intention as
    an observation. `check_archive_storage.py` is what confirms it against the bucket
    itself; this reports what the last push proved.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import archive_storage
    return {'sources/' + r['key']
            for r in archive_storage.read_manifest(archive_storage.STATE).values()}


def rows_of(name):
    p = os.path.join(DATA, f'{name}.csv')
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def years(rows):
    ys = set()
    for r in rows:
        for k in ('fy', 'edition', 'fy_report'):
            if r.get(k):
                d = re.sub(r'\D', '', r[k])[:4]
                if d:
                    ys.add(d)
                break
    return f'{min(ys)}–{max(ys)}' if ys else '—'


def db_tables():
    p = os.path.join(DATA, 'lunenburg.db')
    if not os.path.exists(p):
        return set()
    con = sqlite3.connect(p)
    return {n for (n,) in con.execute("select name from sqlite_master where type='table'")}


def pages_in(s):
    out = set()
    for a, b in re.findall(r'(\d+)\s*[-–]\s*(\d+)', s or ''):
        if int(b) >= int(a) and int(b) - int(a) < 40:
            out.update(range(int(a), int(b) + 1))
    for n in re.findall(r'(?<![\d-])(\d{1,3})(?![\d-])', s or ''):
        out.add(int(n))
    return out


def places(rel, tracked, stored):
    """Where a file exists, named plainly. The column that matters in BACKUP.md."""
    where = ['tree']
    if rel in tracked:
        where.append('git')
    if rel in stored:
        where.append('bucket')
    return ' + '.join(where) if len(where) > 1 else '**working tree only**'


def build_backup():
    tracked = tracked_files()
    stored = stored_files()
    docs = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')

    # copies of each annual report
    single = []
    for f in sorted(os.listdir(docs)) if os.path.isdir(docs) else []:
        rel = f'sources/town-annual-reports/docs/{f}'
        if rel not in tracked and rel not in stored:
            single.append((f, os.path.getsize(os.path.join(docs, f))))

    STAGES = [
        ('sources/town-budget/docs/', 'The town\'s PDFs. The primary source, and the only '
         'thing here that is not a function of something else.',
         're-download from two published addresses — **if they still resolve**'),
        ('sources/town-budget/ocr/', 'OCR geometry: `page, x, y, w, h, conf, text` per '
         'recognised line, Apple Vision at raster scale 6.0 with per-page orientation '
         'calibration.', '**~2 hours of compute**'),
        ('sources/town-budget/pages/', 'Each page as text, in two renderings — the PDF\'s '
         'own text layer, and the OCR geometry rebuilt into a fixed-width page.',
         '~5 minutes, given the OCR'),
        ('sources/town-budget/text/', 'Extracted plain text per document, what '
         '`search_minutes.py` and the classifiers read.', 'minutes'),
        ('sources/data/inventory/', 'Per-report table catalogues — every table found by '
         'reading all sixteen reports end to end, printed heading verbatim.',
         '**many hours of agent reading**'),
        ('sources/data/rosters/', 'Roster page dumps and parsed JSON — 100 pages, every '
         'line numbered and accounted for.', '**many hours of agent reading**'),
        ('sources/data/', 'The datasets themselves, plus provenance and the extraction '
         'plan. CSV only — the directory total below includes the two above.',
         'seconds, given everything above'),
        ('sources/data/lunenburg.db', 'Derived read model. Dropped and rebuilt from the '
         'CSVs on every run, never edited.', 'seconds — `python3 scripts/build_db.py`'),
    ]

    out = ['# What to back up, where it is, and how many copies of it exist',
           '',
           '**Generated by `scripts/build_archive_guide.py`. Do not edit.**',
           '',
           'Paths are from the repository root. Three places count: this **tree**, '
           '**git**, and the public R2\n'
           '**bucket** the documents were moved to on 5 September 2026. The **copies** '
           'column is the one that '
           'matters: a',
           'path that exists only in the working tree is one disk failure from gone.',
           '',
           '| path | copies | size | files | what it is | cost to lose |',
           '|---|---|---:|---:|---|---|']
    for rel, what, cost in STAGES:
        p = os.path.join(ROOT, rel.rstrip('/'))
        if not os.path.exists(p):
            continue
        size, n = du(p)
        if rel == 'sources/data/':
            size = sum(os.path.getsize(f) for f in glob.glob(os.path.join(DATA, '*.csv')))
            n = len(glob.glob(os.path.join(DATA, '*.csv')))
        if os.path.isfile(p):
            copies = places(rel, tracked, stored)
        else:
            here = {os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')
                    for d, _x, fs in os.walk(p) for f in fs}
            if rel == 'sources/data/':
                here = {os.path.relpath(f, ROOT).replace(os.sep, '/')
                        for f in glob.glob(os.path.join(DATA, '*.csv'))}
            elsewhere = tracked | stored
            safe = len(here & elsewhere)
            kinds = ' + '.join(k for k, sel in (('git', tracked), ('bucket', stored))
                               if here & sel)
            copies = ('**working tree only**' if safe == 0
                      else f'tree + {kinds}' if safe == len(here)
                      else f'tree; **{len(here) - safe} of {len(here)} nowhere else**')
        out.append(f'| `{rel}` | {copies} | {mb(size)} | {n:,} | {what} | {cost} |')

    out += ['',
            '## The files that exist in exactly one place',
            '']
    if single:
        out += [f'**{len(single)} of the sixteen annual town reports are on this machine '
                'and nowhere else.** They are',
                'neither tracked in git nor stored in the R2 archive, so losing this '
                'working tree loses them and',
                'the town\'s own links are the only other copy.',
                '',
                '| report | size |',
                '|---|---:|']
        for f, size in sorted(single, key=lambda t: -t[1]):
            out.append(f'| `{f}` | {mb(size)} |')
        out += ['',
                'The fix is one command: `python3 scripts/sync_archive.py --manifest '
                '--push`, which uploads',
                'them, reads each back, and compares the sha256 before recording it as '
                'stored.']
    else:
        out.append('None — every annual report has at least two copies, and since '
                   '5 September 2026 one of')
        out.append('them is off this machine: the six that used to exist only in this '
                   'working tree are in the')
        out.append('R2 archive.')

    out += ['',
            '## What is deliberately NOT stored',
            '',
            '**Rendered page images.** A page is 1–3 MB as a PNG and there are 2,751 of '
            'them, holding',
            'nothing the geometry does not already carry. Regenerate any page with:',
            '',
            '    swift scripts/render_page.swift <pdf> <page> out.png 3.0',
            '',
            '**Verification packets.** `scripts/verify_against_page.py` builds a page image '
            'beside the rows',
            'extracted from it, on demand, into `sources/data/verify/`. That directory is '
            'scratch.',
            '']
    return '\n'.join(out)


def build_guide():
    tables = db_tables()
    prov = {os.path.basename(p)[len('PROVENANCE-'):-3]
            for p in glob.glob(os.path.join(DATA, 'PROVENANCE-*.md'))}
    src = open(os.path.join(ROOT, 'scripts', 'build_source_index.py')).read()

    def line(name, what, proof=''):
        rows = rows_of(name)
        if not rows:
            return None
        st = collections.Counter(r.get('status', '') for r in rows)
        indb = 'yes' if name.replace('-', '_') in tables else '**no**'
        pub = 'yes' if f"'data/{name}.csv'" in src else '**no**'
        pr = 'yes' if name in prov else ('shared' if name.startswith('report-') else '—')
        # A dataset with no `status` column is not "0 checked" -- it is proved a different
        # way, and printing zeros where a proof belongs reads as unverified.
        graded = st['checked'] + st['check failed'] + st['no check']
        state = (f"{st['checked']:,} checked / {st['check failed']:,} failed / "
                 f"{st['no check']:,} no check" if graded else (proof or '—'))
        return (f'| `{name}.csv` | {len(rows):,} | {years(rows)} | {state} | {indb} | '
                f'{pr} | {pub} |')

    out = ['# The annual town reports: what we have, where it is, and what is missing',
           '',
           '**Generated by `scripts/build_archive_guide.py`. Do not edit.**',
           '',
           'Sixteen annual town reports, FY2011–FY2025, read page by page. Start here.',
           '',
           '| you want | read |',
           '|---|---|',
           '| what a figure means, before quoting one | `sources/data/PROVENANCE-report-tables.md` |',
           '| where a row came from | `sources/data/dataset-provenance.csv`, `notes/generated/DATASET-PROVENANCE.md` |',
           '| what is on disk and how many copies | `notes/reference/BACKUP.md` |',
           '| how a PDF becomes a database row | `sources/town-budget/PIPELINE.md` |',
           '| what is half-done and what is risky | `notes/HANDOFF-ANNUAL-REPORTS.md` |',
           '| how the reader was built and what broke it | `notes/findings/TOWN-ARCHIVE.md` |',
           '| the database grain | `notes/reference/SCHEMA.md` |',
           '',
           '## The datasets',
           '',
           'Every row carries the page it came from. `status` is per table-run: `checked` '
           'means a check',
           'existed and passed, `check failed` that one existed and did not, `no check` '
           'that the table',
           'prints no total. **Nothing here may be aggregated without splitting on '
           '`status` first.**',
           '',
           '### Built by a dedicated extractor',
           '',
           '| dataset | rows | years | state | in db | provenance | published |',
           '|---|---:|---|---|---|---|---|']
    for name, what, proof in HAND:
        r = line(name, what, proof)
        if r:
            out.append(r)
    out += ['',
            '### Built by the generic extractor (`scripts/extract_tables.py`)',
            '',
            '`v1`…`v8` are ORDINALS — the first, second, third column of **that page** that '
            'held figures.',
            'Read `column_meaning` before reading a value.',
            '',
            '| dataset | rows | years | state | in db | provenance | published |',
            '|---|---:|---|---|---|---|---|']
    for p in sorted(glob.glob(os.path.join(DATA, 'report-*.csv'))):
        name = os.path.basename(p)[:-4]
        if name == 'report-anomalies':
            continue
        r = line(name, '')
        if r:
            out.append(r)
    out += ['',
            '### About the documents rather than the town',
            '',
            '| dataset | rows | years | what it is |',
            '|---|---:|---|---|']
    for name, what in ABOUT:
        rows = rows_of(name)
        if rows:
            out.append(f'| `{name}.csv` | {len(rows):,} | {years(rows)} | {what} |')

    # --- what is uncaptured -------------------------------------------------------
    cat = rows_of('annual-report-catalogue')
    plan = rows_of('extraction-plan')
    planned = collections.defaultdict(set)
    for r in plan:
        planned[r['edition']] |= pages_in(r['pages'])
    uncovered = [r for r in cat if not (pages_in(r['pages']) & planned.get(r['edition'], set()))]
    est = 0
    for r in uncovered:
        try:
            est += int(re.sub(r'\D', '', r['approx_rows']) or 0)
        except ValueError:
            pass
    names = collections.Counter(r['name'][:58] for r in uncovered
                                if r['extractable'] == 'clean')

    ds_planned = collections.defaultdict(set)
    for r in plan:
        ds_planned[r['dataset']].add(r['edition'])
    FILE = {'receipts': 'annual-report-receipts', 'special_revenue': 'special-revenue-funds',
            'school_rosters': 'staff-roster-entries'}
    empty = []
    for d, eds in sorted(ds_planned.items()):
        f = FILE.get(d, 'report-' + d.replace('_', '-'))
        rows = rows_of(f)
        if not rows:
            continue
        key = 'edition' if 'edition' in rows[0] else 'fy'
        got = {(r[key] if key == 'edition' else 'FY' + r['fy']) for r in rows}
        miss = sorted(eds - got)
        if miss:
            empty.append((d, len(eds) - len(miss), len(eds), miss))

    out += ['',
            '## What is NOT captured',
            '',
            f'### 1. {len(uncovered)} of {len(cat)} catalogued tables sit on pages no '
            f'dataset reads',
            '',
            f"About {est:,} rows by the catalogue's own estimate. Much of it is furniture "
            '— tables of',
            'contents, pie-chart labels, phone directories. These are the substantial ones, '
            'all marked',
            '`clean` in the catalogue:',
            '',
            '| times | table |',
            '|---:|---|']
    SKIP = ('contents', 'phone', 'profile', 'memoriam', 'legislator', 'hours')
    shown = 0
    for n, c in names.most_common(40):
        if any(k in n.lower() for k in SKIP):
            continue
        out.append(f'| {c} | {n} |')
        shown += 1
        if shown >= 14:
            break
    out += ['',
            '### 2. Editions the plan asks for that produced no rows',
            '',
            'A run that fails prints a line. A run that never happens printed nothing, '
            'which is how',
            'fourteen years of the Montachusett assessment went missing without anybody '
            'noticing.',
            '`extract_tables.py` now prints this count on every run.',
            '',
            '| dataset | got | planned | missing |',
            '|---|---:|---:|---|']
    for d, got, tot, miss in empty:
        out.append(f'| `{d}` | {got} | {tot} | {", ".join(miss)} |')

    out += ['',
            '### 3. Rows the chosen rendering does not hold',
            '',
            'The extractor picks OCR or the text layer per page for its columns and never '
            'notices the',
            'other holds more rows. `County Retirement Assessment $967,652.00` is printed '
            'on FY2016',
            "page 30 and absent from Vision's OCR of it, so it is absent from the dataset. "
            '22 money',
            'pages fail that audit. The omnibus reader takes whichever rendering holds more '
            'lines; the',
            "accountant's schedule cannot, because it needs the geometry.",
            '',
            '### 4. No analysis rests on any of it',
            '',
            'Every dataset above is queryable, citable and published, and none of it appears '
            'in a written',
            'argument. Two standing questions in `CLAUDE.md` were answered from these '
            'documents —',
            'placement counts, and the bound on staffing — and no document tells a resident '
            'either thing.',
            '',
            '## Running it',
            '',
            '    python3 scripts/report_pages.py --rebuild          # page cache; REQUIRED after any OCR change',
            '    python3 scripts/extract_tables.py --list',
            '    python3 scripts/extract_tables.py <dataset>        # one table family',
            '    python3 scripts/verify_report_tables.py            # every stated reconciliation, recomputed',
            '    python3 scripts/verify_against_page.py <ds> <ed>   # the page image beside the rows',
            '    python3 scripts/build_db.py --check                # reload; 19 reconciliations must tie',
            '    python3 scripts/build_archive_guide.py             # regenerate this page and BACKUP.md',
            '',
            '**A fix upstream of the page cache does nothing until the cache is rebuilt.**',
            '']
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    made = {GUIDE: build_guide(), BACKUP: build_backup()}
    stale = [p for p, body in made.items()
             if not os.path.exists(p) or open(p).read() != body]
    if args.check:
        for p in stale:
            print(f'  STALE  {os.path.relpath(p, ROOT)}')
        if stale:
            print(f'\n{len(stale)} page(s) stale. Run: python3 scripts/build_archive_guide.py')
            sys.exit(1)
        print('both archive guides are current')
        return
    for p, body in made.items():
        open(p, 'w').write(body)
        print(f'wrote {os.path.relpath(p, ROOT)}')


if __name__ == '__main__':
    main()
