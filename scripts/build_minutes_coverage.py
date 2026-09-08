#!/usr/bin/env python3
"""How much of the town's decision-making is on the record, per board, per year.

    python3 scripts/build_minutes_coverage.py            # crawl and write
    python3 scripts/build_minutes_coverage.py --check    # fail if the file is stale
    python3 scripts/build_minutes_coverage.py --offline  # recompute from what we hold

WHAT THIS MEASURES, AND THE PROXY IT RESTS ON (rule 7)

For every board and year the town's AgendaCenter lists, this records how many AGENDAS were
posted and how many sets of MINUTES. The ratio is the headline.

**The denominator is agendas posted, not meetings held.** Those are different quantities and
nothing published reconciles them: a meeting can be held with no agenda posted, and an
agenda can be posted for a meeting later cancelled. So this bounds the question rather than
settling it, and every figure it produces must be described as minutes against AGENDAS.
Calling it "minutes against meetings held" would be a proxy quoted as the thing.

WHY IT IS WORTH MEASURING ANYWAY

Rule 15a says to search the meeting archive for what people said about a thing. That
instruction is only as good as the record, and the record is uneven: School Committee posted
49 agendas in 2023 and 9 sets of minutes. A search that finds nothing in that year is not
evidence nobody said it — it is evidence that four meetings in five left no readable trace.

`search_minutes.py` prints a coverage line for exactly this reason. Until this dataset
existed that line compared what we hold against what we hold, and called the result what the
town published.

CRAWLING IS THE POINT AND ALSO THE COST. The live counts come from the town's own listing,
which is the only authority on what exists. `--offline` recomputes from sources/meetings/
index.csv instead, which answers a narrower question -- what we HOLD -- and is what the
--check mode uses so a build never depends on the town's website being up.
"""
import argparse
import csv
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'minutes-coverage.csv')
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
FIELDS = ['board', 'year', 'agendas', 'minutes', 'minutes_share', 'basis']


def _fetcher():
    spec = importlib.util.spec_from_file_location(
        'fa', os.path.join(ROOT, 'scripts', 'fetch_agendas.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def from_town(first, last):
    """Crawl the AgendaCenter. The authority on what EXISTS."""
    fa = _fetcher()
    cats = fa.categories()
    if not cats:
        raise SystemExit('the AgendaCenter listed no boards at all. That is a fetch '
                         'failure, not a town with no committees -- refusing to write.')
    rows = []
    for cid, name in sorted(cats.items(), key=lambda kv: kv[1]):
        for year in range(first, last + 1):
            got = fa.listing(cid, year)
            if not got:
                continue
            a = sum(1 for k, _, _ in got if k == 'agenda')
            m = sum(1 for k, _, _ in got if k == 'minutes')
            rows.append(dict(board=name, year=year, agendas=a, minutes=m,
                             minutes_share=(round(m / a, 4) if a else ''),
                             basis='town listing'))
    return rows


def from_disk():
    """What we HOLD. A narrower question, and it needs no network."""
    if not os.path.exists(INDEX):
        raise SystemExit('sources/meetings/index.csv is absent; nothing to count.')
    seen = {}
    for r in csv.DictReader(open(INDEX, encoding='utf-8', errors='replace')):
        y = (r.get('date') or '')[:4]
        if not y.isdigit():
            continue
        k = (r['board'], int(y))
        seen.setdefault(k, {'agenda': 0, 'minutes': 0})
        kind = r.get('kind')
        if kind in seen[k]:
            seen[k][kind] += 1
    rows = [dict(board=b, year=y, agendas=v['agenda'], minutes=v['minutes'],
                 minutes_share=(round(v['minutes'] / v['agenda'], 4) if v['agenda'] else ''),
                 basis='held')
            for (b, y), v in sorted(seen.items())]
    if not rows:
        raise SystemExit('the meetings index parsed to zero board-years. A count that '
                         'matches nothing looks exactly like a town with no meetings.')
    return rows


def write(rows):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='first', type=int, default=2009)
    ap.add_argument('--to', dest='last', type=int, default=2026)
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    rows = from_disk() if (a.offline or a.check) else from_town(a.first, a.last)

    if a.check:
        if not os.path.exists(OUT):
            print('STALE — %s has never been written' % os.path.relpath(OUT, ROOT))
            return 1
        have = [r for r in csv.DictReader(open(OUT, encoding='utf-8'))
                if r['basis'] == 'held']
        made = {(r['board'], str(r['year'])): (str(r['agendas']), str(r['minutes']))
                for r in rows}
        old = {(r['board'], r['year']): (r['agendas'], r['minutes']) for r in have}
        if made != old:
            print('STALE — the held counts no longer reproduce from '
                  'sources/meetings/index.csv. Run scripts/build_minutes_coverage.py '
                  '--offline (or a full crawl to refresh the town-listing rows).')
            return 1
        print('ok — %d board-years of held coverage reproduce' % len(have))
        return 0

    # A crawl replaces the town-listing rows and keeps whatever held rows exist, so the
    # two bases can be compared without a second crawl.
    if not a.offline and os.path.exists(OUT):
        keep = [r for r in csv.DictReader(open(OUT, encoding='utf-8'))
                if r['basis'] == 'held']
        rows = rows + keep
    elif a.offline and os.path.exists(OUT):
        keep = [r for r in csv.DictReader(open(OUT, encoding='utf-8'))
                if r['basis'] == 'town listing']
        rows = keep + rows

    write(rows)
    boards = len({r['board'] for r in rows})
    ag = sum(int(r['agendas']) for r in rows)
    mi = sum(int(r['minutes']) for r in rows)
    print('wrote %s — %d board-years, %d boards, %d agendas, %d minutes (%.0f%%)'
          % (os.path.relpath(OUT, ROOT), len(rows), boards, ag, mi,
             (mi / ag * 100) if ag else 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
