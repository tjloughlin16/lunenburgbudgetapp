#!/usr/bin/env python3
"""A document the publisher re-posts at a new address is caught as a REPLACEMENT.

The case it replays: on 3 November 2026 the town replaced the 1997 and 1999 annual reports
with rescans at new addresses (DocumentCenter/View/4615, 4616) and let the old ones (4523,
4525) answer 404. Nothing caught it. See notes/findings/ANNUAL-REPORT-RESCANS-2026-11.md.

    python3 scripts/test_publisher_replacements.py           # offline, a stub stands in for the town
    python3 scripts/test_publisher_replacements.py --live    # also asks the town's own server

The `before` catalogue is the one git held before the rescans were landed (dff3cb6f6^), so the
replay sees exactly what the quarterly watch would have seen.
"""
import csv
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import verify_source_copies as V  # noqa: E402
import watch_documents as W  # noqa: E402

INDEX = 'sources/town-annual-reports/index.csv'
LANDED = 'dff3cb6f6'          # the commit that landed the rescans
TOWN = 'https://www.lunenburgma.gov/DocumentCenter/View/'
FAIL = []


def expect(what, got, want):
    ok = got == want
    print(f'  {"ok  " if ok else "FAIL"} {what}: {got!r}' + ('' if ok else f'  (wanted {want!r})'))
    if not ok:
        FAIL.append(what)


def rows_at(rev):
    out = subprocess.run(['git', 'show', f'{rev}:{INDEX}'], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    return list(csv.DictReader(io.StringIO(out)))


def replay(probe, label):
    print(f'\nreplay of the 3 November rescans, {label}')
    before = rows_at(LANDED + '^')
    after = rows_at(LANDED)
    for new_id, old_id, year in (('4615', '4523', 1997), ('4616', '4525', 1999)):
        row = next(r for r in after if r['upstream'] == TOWN + new_id)
        kind, replaces = W.replacement_verdict(row, before, probe)
        expect(f'{year}: View/{new_id} is', kind, 'replacement')
        expect(f'{year}: and it replaces', replaces,
               f'sources/town-annual-reports/docs/{old_id}-{year}-annual-town-report.pdf')
    return before, after


def main():
    live = '--live' in sys.argv
    dead = {TOWN + '4523', TOWN + '4525'}
    stub = lambda u: '404' if u in dead else '200'

    before, after = replay(stub, 'the town stubbed: 4523 and 4525 answer 404')
    if live:
        replay(V.status_of, "asking the town's server")

    print('\nthe verdicts that must NOT be replacement')
    row = next(r for r in after if r['upstream'] == TOWN + '4615')
    expect('old address still served', W.replacement_verdict(row, before, lambda u: '200')[0],
           'possible replacement')
    expect('old address only failing (503)', W.replacement_verdict(row, before, lambda u: '503')[0],
           'possible replacement')
    fresh = dict(row, label='2026 Annual Town Report', local='sources/x/new.pdf')
    expect('a title nobody holds', W.replacement_verdict(fresh, before, stub), ('new', ''))
    twice = before + [dict(r, local=r['local'] + '.copy') for r in before
                      if r['label'] == '1997 Annual Town Report']
    expect('a title two held rows share', W.replacement_verdict(row, twice, stub), ('new', ''))
    held = next(r for r in before if r['label'] == '1998 Annual Town Report')
    alias = dict(held, upstream=held['upstream'] + ' https://example.org/1998.pdf')
    expect('a new address for a held copy', W.replacement_verdict(alias, before, stub)[0],
           'new address')

    print('\nverify_source_copies: what a dead address is recorded as')
    for code, want in (('404', 'gone'), ('410', 'gone'), ('500', 'unreachable'),
                       ('503', 'unreachable'), ('000', 'unreachable'), ('403', 'unreachable')):
        expect(f'HTTP {code}', V.classify('/dev/null', '/dev/null', code), want)

    print('\nverify_source_copies: a space-joined upstream is two checks')
    items = V.eligible(['town-annual-reports/'])
    expect('addresses holding whitespace', sum(any(c.isspace() for c in u) for _, u in items), 0)
    fy11 = sorted(u for p, u in items if '4117-fy-2011' in p)
    expect('FY2011 addresses checked', fy11,
           sorted([TOWN + '4117', 'https://www.lunenburgma.gov/ArchiveCenter/ViewFile/Item/121']))

    print(f'\n{"FAILED: " + ", ".join(FAIL) if FAIL else "all passed"}')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
