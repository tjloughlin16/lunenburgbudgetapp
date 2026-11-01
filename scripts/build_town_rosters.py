#!/usr/bin/env python3
"""Town officials and staff, edition by edition, as the annual reports print them.

The school side is `build_staff_rosters.py`. This is the town side: the officers' directory
at the front of nearly every annual town report, 1959-2010 and FY2011-FY2025 -- who was
elected to what, who was appointed to what, usually with the year the term ends.

Reads the per-page reads in `sources/data/town-rosters/` (`<edition>-p<NNN>.json`, made by
`read_town_roster_pages.py` from the numbered dumps `dump_town_roster_pages.py` writes),
checks them, and writes:

    sources/data/town-roster-entries.csv     one row per name per position per edition
    sources/data/PROVENANCE-town-rosters.md  what was read, the line accounting, the gaps

## The check

A list of officers prints no total, so there is nothing to reconcile against. The check is
**line accounting**, as for the school rosters: every non-blank line of every page is
claimed -- as an entry, a heading, or a line that is not a town official (page furniture,
a state or federal officeholder, a vacancy, prose, a wrapped note) -- and **this refuses to
write if any page leaves a line unclaimed.** The second check is attribution: every entry's
name must be printed on the line it was attributed to. That catches the error line
accounting cannot, a column read one row out of step.

## What a row is, and is not

A row is a NAME THE REPORT PRINTED under a heading. It is not proof the person served the
whole year, nor that a seat was filled (vacancies are not rows), and the report's list is a
point in time it does not date. `year` is the edition's own year: the CALENDAR year for
the 1959-2010 editions and the FISCAL year for FY2011-FY2025 -- the two are not the same
kind of year and the column does not pretend they are (`edition` says which). `section` is printed text; `kind` is ours, derived from it
by rule (`ELECT` -> elected, `APPOINT` -> appointed, else `not stated`; every entry on a
department page -- a fire or police roster inside a department's report -- is `department
roster`) so committee members, officers and staff can be told apart by what the page says.

State and federal officeholders printed in the same directory (senators, representatives,
the governor) are not town officials and are not rows; their lines are claimed as
`not-a-town-office` and counted.

    python3 scripts/build_town_rosters.py [--check]
"""

import argparse
import collections
import csv
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
DIR = os.path.join(DATA, 'town-rosters')
PAGES = os.path.join(DIR, 'PAGES.csv')
ENTRIES = os.path.join(DATA, 'town-roster-entries.csv')
PROV = os.path.join(DATA, 'PROVENANCE-town-rosters.md')
NOT_FOUND = os.path.join(DIR, 'NOT-FOUND.csv')

FIELDS = ['edition', 'year', 'page', 'line', 'kind', 'kind_flag', 'section', 'position', 'name', 'term',
          'note', 'document', 'href']


# THE 1991 REPORT PRINTS ITS TWO HEADINGS SWAPPED. Page 4 line 2 reads `APPOINTED` above the
# Moderator, the Board of Selectmen, the School Committee and the Library Trustees -- every
# one an elected office in every other edition -- and page 4 line 32 reads `ELECTED` above
# the Agent of Veterans' Services, the Animal Control Officer and the Board of Appeals.
# `section` keeps what is printed (rule 13); `kind` is swapped for this edition only.
SWAPPED_HEADINGS = {'1991'}


def kind_of(section, edition=''):
    k = _kind(section)
    if edition in SWAPPED_HEADINGS:
        return {'elected': 'appointed', 'appointed': 'elected'}.get(k, k)
    return k


def position_key(pos):
    """A position's name without its term text, for comparing it across editions."""
    p = re.split(r'\s*[-\u2013(]\s*(\d|term|\()', pos.upper())[0]
    return re.sub(r'[^A-Z ]', '', p).replace('  ', ' ').strip()


def flag_kinds(rows):
    """`kind_flag` = `minority` where a row's elected/appointed kind disagrees with what the
    same position is in at least 80% of its other rows. In 1993 and 1994 the directory
    runs the elected and appointed lists side by side in shared columns, and the reader
    can carry the wrong section heading across; this makes those rows findable rather than
    silently wrong. A flag, not a correction: the majority can be wrong too."""
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        if r['kind'] in ('elected', 'appointed'):
            by[position_key(r['position'])][r['kind']] += 1
    for r in rows:
        r['kind_flag'] = ''
        c = by.get(position_key(r['position']))
        if r['kind'] not in ('elected', 'appointed') or not c:
            continue
        top, n = c.most_common(1)[0]
        if top != r['kind'] and n >= 0.8 * sum(c.values()) and sum(c.values()) >= 5:
            r['kind_flag'] = 'minority'
    return rows


def _kind(section):
    s = (section or '').upper()
    # Whole words: SELECTMEN contains ELECT, so `Appointed by Selectmen:` was read as both.
    ap = bool(re.search(r'\bAPPOINT', s))
    el = bool(re.search(r'\bELECT', s))
    # `Town Officials / Elected and Appointed` (1984) names both and settles neither.
    if ap and el:
        return 'not stated'
    if ap:
        return 'appointed'
    if el:
        return 'elected'
    return 'not stated'
    if 'APPOINT' in s:
        return 'appointed'
    if 'ELECT' in s:
        return 'elected'
    return 'not stated'


def numbered(path):
    out = {}
    for raw in open(path, encoding='utf-8'):
        m = re.match(r'\s*(\d+)\| ?(.*)$', raw.rstrip('\n'))
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def tokens(text):
    return re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text or '')


def clean(s):
    return ' '.join(str(s or '').split())


def build():
    plan = list(csv.DictReader(open(PAGES, newline='', encoding='utf-8')))
    rows, ledger, refusals, unread = [], [], [], []
    why_n = collections.Counter()
    relocated = []
    cost = 0.0
    for p in plan:
        ed, page = p['edition'], int(p['page'])
        base = os.path.join(DIR, '%s-p%03d' % (ed, page))
        if not os.path.exists(base + '.json'):
            unread.append('%s p%d' % (ed, page))
            continue
        doc = json.load(open(base + '.json', encoding='utf-8'))
        lines = numbered(base + '.txt')
        total = len(lines)
        if doc.get('lines_on_page') != total:
            refusals.append('%s p%d: read from %s lines, the dump now has %d -- re-read it'
                            % (ed, page, doc.get('lines_on_page'), total))
        claimed, bad = set(), []
        for e in doc['entries']:
            n = e['line']
            if n not in lines:
                bad.append('line %s out of range' % n)
                continue
            claimed.add(n)
            here = re.sub(r'@\d\d', ' ', lines[n]).lower()
            miss = [t for t in tokens(e['name']) if t.lower() not in here]
            if miss:
                bad.append('line %d: %r not printed there' % (n, e['name']))
        claimed |= {n for n in doc['headings'] if n in lines}
        for g in doc['ignored']:
            if g['line'] in lines:
                claimed.add(g['line'])
                why_n[g['why']] += 1
        missing = sorted(set(range(1, total + 1)) - claimed)
        if missing:
            refusals.append('%s p%d: %d of %d lines unclaimed (%s)'
                            % (ed, page, len(missing), total, missing[:12]))
        if bad:
            refusals.append('%s p%d: %d names not on their line: %s'
                            % (ed, page, len(bad), '; '.join(bad[:5])))
        relocated += [dict(r, page='%s p%d' % (ed, page)) for r in doc.get('relocated', [])]
        cost += float(doc.get('cost_usd') or 0)
        year = int(re.sub(r'\D', '', ed))
        href = '/docs/town-annual-reports/docs/%s#page=%d' % (doc['document'], page)
        n_ent = 0
        for e in doc['entries']:
            name = clean(e['name'])
            if not name:
                continue
            n_ent += 1
            rows.append(dict(edition=ed, year=year, page=page, line=e['line'],
                             kind=('department roster' if doc.get('list') == 'department'
                                   else kind_of(e['section'], ed)), section=clean(e['section']),
                             position=clean(e['position']), name=name,
                             term=clean(e['term']), note=clean(e['note']),
                             document=doc['document'], href=href))
        ledger.append(dict(edition=ed, page=page, lines=total, claimed=len(claimed),
                           entries=n_ent, headings=len(set(doc['headings'])),
                           ignored=len(doc['ignored']), model=doc.get('model', ''),
                           tries=doc.get('tries', 1)))
    flag_kinds(rows)
    rows.sort(key=lambda r: (r['year'], r['edition'], r['page'], r['line'], r['name']))
    return rows, ledger, refusals, unread, why_n, relocated, cost, plan


def entries_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def not_found():
    if not os.path.exists(NOT_FOUND):
        return []
    return list(csv.DictReader(open(NOT_FOUND, newline='', encoding='utf-8')))


def provenance(rows, ledger, why_n, relocated, cost, plan):
    eds = sorted({r['edition'] for r in ledger}, key=lambda e: int(re.sub(r'\D', '', e)))
    tot = sum(r['lines'] for r in ledger)
    acc = sum(r['claimed'] for r in ledger)
    kinds = collections.Counter(r['kind'] for r in rows)
    L = ['# Town officials and staff -- what was read, and what a row means', '',
         '**Generated by `scripts/build_town_rosters.py`. Do not edit.**', '',
         'One row of `town-roster-entries.csv` is one name the annual town report printed',
         'under one heading in one edition. It is not proof the person served the whole',
         'year or that a seat was filled: vacancies are not rows, and the report does not',
         'date its list within the year. Names are printed by the town and kept (see',
         '`notes/process/DATA-PRIVACY.md`).', '',
         '## The check: line accounting', '',
         'A list of officers prints no total, so nothing reconciles. Every non-blank line',
         'of every page is claimed as an entry, a heading, or a line that is not a town',
         'official, and the build refuses to write if a page leaves one unclaimed. Every',
         "entry's name is also checked against the printed line it was attributed to.", '',
         '**%d of %d lines accounted for** across %d pages of %d editions; %d entries.'
         % (acc, tot, len(ledger), len(eds), len(rows)), '',
         'Lines claimed as not an entry, by reason: ' +
         ', '.join('%s %d' % (k, v) for k, v in sorted(why_n.items())) + '.', '',
         '`kind` is ours, derived by rule (APPOINT -> appointed, ELECT -> elected, a page '
         'registered as a department list -> department roster, else not stated): %s.'
         % ', '.join('%s %d' % (k, v) for k, v in sorted(kinds.items())), '',
         '**%d rows carry `kind_flag = minority`**: their elected/appointed kind disagrees '
         'with what the same position is in at least 80%% of its other rows. Most are the '
         '1993 and 1994 directories, which run the two lists side by side in shared columns. '
         'The 1991 report prints its ELECTED and APPOINTED headings swapped (p4 lines 2 and '
         '32); `section` keeps the print and `kind` is swapped for that edition.'
         % sum(1 for r in rows if r.get('kind_flag')), '',
         '## How the pages were read', '',
         'Pages were located by reading each edition (`town-rosters/PAGES.csv`), dumped',
         'with each printed run\'s left edge (`@NN`) because the directory is printed in',
         'columns, and read one page at a time by a language model in an isolated call',
         '(`read_town_roster_pages.py`), which places each name under the heading above it.',
         'An entry whose name sat on the line directly above or below the one it was given',
         'was moved there by that evidence: %d such moves, listed below.' % len(relocated), '',
         'Model cost recorded on the pages: $%.2f API-equivalent.' % cost, '']
    nf = not_found()
    if nf:
        L += ['## Lists looked for and not found', '',
              'Each is a statement about what was searched, not a claim the town never',
              'printed it (rule 13c).', '', '| edition | list | pages and searches |',
              '|---|---|---|']
        for r in nf:
            L.append('| %s | %s | %s |' % (r['edition'], r['list'], r['searched']))
        L.append('')
    L += ['## Per page', '', '| edition | page | lines | claimed | entries | headings | '
          'not entries |', '|---|---:|---:|---:|---:|---:|---:|']
    for r in ledger:
        L.append('| %s | %d | %d | %d | %d | %d | %d |' % (
            r['edition'], r['page'], r['lines'], r['claimed'], r['entries'], r['headings'],
            r['ignored']))
    L.append('')
    if relocated:
        L += ['## Entries moved to the adjacent line their name is printed on', '',
              '| page | name | from | to |', '|---|---|---:|---:|']
        for r in relocated:
            L.append('| %s | %s | %s | %s |' % (r['page'], r['name'], r['from'], r['to']))
        L.append('')
    return '\n'.join(L) + '\n'


def runs(rows, top=10):
    """The longest runs, by the SAME rule the school rosters use: `name_key` and
    `MAX_ABSENT` are imported from build_historical_report, so the two rankings cannot
    drift apart. A name's run breaks when it is absent from more than MAX_ABSENT
    consecutive editions held."""
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    from build_historical_report import MAX_ABSENT, name_key
    held = sorted({int(r['year']) for r in rows})
    by = collections.defaultdict(list)
    for r in rows:
        by[name_key(r['name'])].append(r)
    out = []
    for k, rs in by.items():
        ys = sorted({int(r['year']) for r in rs})
        cur, chunks = [ys[0]], []
        for y in ys[1:]:
            if len([h for h in held if cur[-1] < h < y]) > MAX_ABSENT:
                chunks.append(cur)
                cur = [y]
            else:
                cur.append(y)
        chunks.append(cur)
        for ch in chunks:
            inside = [r for r in rs if ch[0] <= int(r['year']) <= ch[-1]]
            forms = [r['name'] for r in inside]
            pos = collections.Counter(r['position'].split('-')[0].strip().title()
                                      for r in inside)
            out.append(dict(key=k, name=max(forms, key=lambda n: (forms.count(n), len(n))),
                            first=ch[0], last=ch[-1], span=ch[-1] - ch[0], seen=len(ch),
                            positions=[p for p, _ in pos.most_common(4)]))
    out.sort(key=lambda r: (-r['span'], -r['seen'], r['key']))
    return out[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--runs', action='store_true', help='print the 10 longest runs')
    args = ap.parse_args()
    rows, ledger, refusals, unread, why_n, relocated, cost, plan = build()
    if unread:
        print('%d planned pages not yet read: %s' % (len(unread), ', '.join(unread[:20])))
    if refusals:
        print('REFUSING -- pages that do not account:')
        for r in refusals:
            print('  ' + r)
        raise SystemExit(1)
    csv_text = entries_csv(rows)
    prov = provenance(rows, ledger, why_n, relocated, cost, plan)
    if args.check:
        stale = [p for p, want in ((ENTRIES, csv_text), (PROV, prov))
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != want]
        if stale or unread:
            for p in stale:
                print('STALE: %s' % os.path.relpath(p, ROOT))
            raise SystemExit(1)
        print('town rosters reproduce: %d entries, %d pages' % (len(rows), len(ledger)))
        return
    for path, text in ((ENTRIES, csv_text), (PROV, prov)):
        with open(path + '.tmp', 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
        os.replace(path + '.tmp', path)
    print('%d pages, %d of %d lines accounted for, %d entries, %d editions'
          % (len(ledger), sum(r['claimed'] for r in ledger), sum(r['lines'] for r in ledger),
             len(rows), len({r['edition'] for r in ledger})))
    print('wrote %s, %s' % (os.path.relpath(ENTRIES, ROOT), os.path.relpath(PROV, ROOT)))
    if args.runs:
        for r in runs(rows):
            print('  %-28s %d-%d  %2d yrs, in %2d editions  %s'
                  % (r['name'], r['first'], r['last'], r['span'], r['seen'],
                     '; '.join(r['positions'])))


if __name__ == '__main__':
    main()
