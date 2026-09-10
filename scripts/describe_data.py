#!/usr/bin/env python3
"""Search the database by the QUESTION you are asking, not by column name.

WHY THIS EXISTS. `sources/data/table-semantics.csv` already records, for every table,
what quantity it holds, at what grain, and what question it answers. It is published at
`/api/table_semantics.json` and `build_db.py` checks that every `default_query` in it
still runs. It is good, and it was invisible at the moment of use.

On 10 September 2026 an agent looking for teacher FTE per school grepped the schema for
column names containing `fte`, found two tables, and reported that FTE by category
existed for teachers only. `dese_teacher_grade_subject` was in the same grep output and
was passed over, because the question had already been framed as "by job class" and a
grade band did not match that shape. Its `what_it_answers` reads, in full:

    Teacher FTE by grade band AND subject AND school. This breaks a limit recorded here
    as structural: the town's staff rosters give grade detail with no FTE, and DESE
    elsewhere gives FTE with no grade detail.

Somebody had already found the thing, written down why it mattered, and filed it. The
failure was not knowledge and not documentation. It was that grep searches the names of
things and the answer was written in prose.

    python3 scripts/describe_data.py "fte per school"
    python3 scripts/describe_data.py "how many children left"
    python3 scripts/describe_data.py --table dese_teacher_grade_subject
    python3 scripts/describe_data.py --undescribed

The ranking is deliberately dumb -- term overlap against `what_it_answers`, `grain`,
`caution` and the table name. It is a router, not a search engine: its job is to put the
three tables you should read in front of you, with the CAUTION attached, so a rollup row
or a level column is met before it is summed rather than after.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMANTICS = os.path.join(ROOT, 'sources', 'data', 'table-semantics.csv')
DATASETS = os.path.join(ROOT, 'sources', 'data', 'dataset-semantics.csv')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')

# Words that appear in half the descriptions and so cannot discriminate between them.
# Not a general stopword list -- these are this archive's own filler.
NOISE = {
    'the', 'a', 'an', 'of', 'in', 'is', 'it', 'and', 'or', 'for', 'to', 'by', 'per',
    'one', 'row', 'each', 'with', 'from', 'that', 'this', 'its', 'as', 'at', 'on',
    'not', 'are', 'was', 'what', 'which', 'how', 'we', 'our', 'table', 'data',
    'every', 'any', 'all', 'has', 'have', 'does', 'do', 'year', 'years',
}


def terms(text):
    return {w for w in re.findall(r'[a-z0-9_]+', (text or '').lower())
            if w not in NOISE and len(w) > 1}


def load_datasets():
    """Datasets that are FILES and not tables.

    A CSV on disk is as real as a table and is invisible to anything that reads
    sqlite_master. `dese-class-size.csv` sat on disk for a day before it was loaded, and
    `dese-ap.csv` and `dese-attrition.csv` still are -- they are pages 9 and 6 of the
    current build order. Data that has not reached the database yet is exactly the data
    somebody is about to build a page on.
    """
    if not os.path.exists(DATASETS):
        return []
    with open(DATASETS, encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        # Present a file the way a table is presented, so ranking and printing are shared.
        r['table_name'] = r.get('dataset', '')
        r['_file'] = True
    return rows


def load_semantics():
    if not os.path.exists(SEMANTICS):
        sys.exit('missing %s' % SEMANTICS)
    with open(SEMANTICS, encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit('%s is empty -- refusing to report that nothing is described' % SEMANTICS)
    return rows


def db_objects():
    """Every table and view actually in the database, with its columns.

    Read from the database rather than from the CSV on purpose: the whole point is to
    catch the case where the two disagree.
    """
    if not os.path.exists(DB):
        return {}
    con = sqlite3.connect(DB)
    out = {}
    for name, kind in con.execute(
            "select name, type from sqlite_master where type in ('table','view') "
            "and name not like 'sqlite_%' order by name"):
        cols = [r[1] for r in con.execute('pragma table_info("%s")' % name)]
        try:
            n = con.execute('select count(*) from "%s"' % name).fetchone()[0]
        except sqlite3.Error:
            n = None          # a view over a table that no longer exists
        out[name] = dict(kind=kind, columns=cols, rows=n)
    con.close()
    return out


def score(row, want, objs):
    """Term overlap, weighted by where the term was found.

    `what_it_answers` is prose somebody wrote to be read by a person asking a question,
    so it carries the most weight. Column names carry the least: matching on them is
    exactly the failure this script exists to correct, but they are not worthless.
    """
    hits = 0.0
    for field, weight in (('what_it_answers', 3.0), ('grain', 2.0),
                          ('table_name', 2.0), ('caution', 1.0)):
        hits += weight * len(want & terms(row.get(field)))
    if row.get('_file'):
        cols = (row.get('columns') or '').split('|')
    else:
        cols = objs.get(row['table_name'], {}).get('columns', [])
    hits += 0.5 * len(want & terms(' '.join(cols)))
    return hits


def show(row, objs, verbose=False):
    name = row['table_name']
    if row.get('_file'):
        n = row.get('rows')
        print('%s   FILE, not in the database -- %s rows, %d columns'
              % (row.get('path') or name, '{:,}'.format(int(n)) if n else '?',
                 len((row.get('columns') or '').split('|'))))
        if not row.get('what_it_answers'):
            print('  NOT DESCRIBED -- nobody has written down what this holds.')
            print('             Read it before using it, and write the row.')
        for label, field in (('grain', 'grain'), ('answers', 'what_it_answers'),
                             ('CAUTION', 'caution'), ('made by', 'generator')):
            if row.get(field):
                print('  %-10s %s' % (label, row[field].strip()))
        if verbose and row.get('columns'):
            print('  columns    %s' % ', '.join(row['columns'].split('|')))
        print()
        return
    obj = objs.get(name, {})
    head = name
    if obj:
        head += '   %s, %s rows, %d columns' % (
            obj['kind'], '{:,}'.format(obj['rows']) if obj['rows'] is not None else '?',
            len(obj['columns']))
    else:
        head += '   NOT IN THE DATABASE'
    print(head)
    if row.get('grain'):
        print('  grain      %s' % row['grain'])
    if row.get('what_it_answers'):
        print('  answers    %s' % row['what_it_answers'].strip())
    if row.get('caution'):
        print('  CAUTION    %s' % row['caution'].strip())
    if verbose:
        if obj.get('columns'):
            print('  columns    %s' % ', '.join(obj['columns']))
        if row.get('default_query'):
            print('  try        %s' % row['default_query'].strip())
    print()


def main():
    ap = argparse.ArgumentParser(
        description='Find the table that answers a question, with its caution attached.')
    ap.add_argument('question', nargs='*', help='what you are trying to find out')
    ap.add_argument('--table', help='show one table in full')
    ap.add_argument('--undescribed', action='store_true',
                    help='database objects with no row in table-semantics.csv')
    ap.add_argument('-n', type=int, default=5, help='how many matches (default 5)')
    ap.add_argument('--json', action='store_true', help='machine-readable')
    args = ap.parse_args()

    rows = load_semantics() + load_datasets()
    objs = db_objects()
    by_name = {r['table_name']: r for r in rows}

    if args.undescribed:
        bare = sorted(r['table_name'] for r in rows
                      if r.get('_file') and not r.get('what_it_answers'))
        missing = sorted(set(objs) - set(by_name))
        stale = sorted(n for n, r in by_name.items()
                       if not r.get('_file') and n not in objs)
        if args.json:
            print(json.dumps(dict(undescribed=missing, described_but_absent=stale), indent=1))
            return 0
        print('%d of %d database objects are described.\n'
              % (len(objs) - len(missing), len(objs)))
        if missing:
            print('NO SEMANTICS -- an agent asking a question cannot find these:')
            for m in missing:
                print('   %-38s %s, %s rows' % (m, objs[m]['kind'],
                      '{:,}'.format(objs[m]['rows']) if objs[m]['rows'] is not None else '?'))
        if stale:
            print('\nDESCRIBED BUT NOT IN THE DATABASE:')
            for s in stale:
                print('   %s' % s)
        if bare:
            print('\n%d FILE dataset(s) with no description -- a page built on one of'
                  '\nthese is a page built on a guess:' % len(bare))
            for b in bare:
                print('   %s' % b)
        return 1 if missing or stale or bare else 0

    if args.table:
        row = by_name.get(args.table)
        if not row:
            near = [n for n in by_name if args.table in n]
            sys.exit('no semantics for %r%s' % (
                args.table, ('\ndid you mean: %s' % ', '.join(near)) if near else ''))
        show(row, objs, verbose=True)
        return 0

    if not args.question:
        ap.print_help()
        return 2

    want = terms(' '.join(args.question))
    if not want:
        sys.exit('nothing to search for once filler words are removed')

    ranked = sorted(((score(r, want, objs), r) for r in rows),
                    key=lambda p: (-p[0], p[1]['table_name']))
    hits = [(s, r) for s, r in ranked if s > 0][:args.n]

    if args.json:
        print(json.dumps([dict(table=r['table_name'], score=s, grain=r.get('grain'),
                               answers=r.get('what_it_answers'), caution=r.get('caution'))
                          for s, r in hits], indent=1))
        return 0

    if not hits:
        print('Nothing matched %r.\n' % ' '.join(args.question))
        print('That is a claim about the WORDS, not about the archive -- the table may')
        print('exist and describe itself differently. Try the quantity rather than the')
        print('question ("headcount", "placements", "assessment"), and read')
        print('  notes/reference/SCHEMA.md   and   sources/data/table-semantics.csv')
        return 1

    print('%d table(s) for %r. Read the CAUTION before you sum anything.\n'
          % (len(hits), ' '.join(args.question)))
    for _, r in hits:
        show(r, objs)
    print('Full record with columns and a worked query:')
    print('  python3 scripts/describe_data.py --table %s' % hits[0][1]['table_name'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
