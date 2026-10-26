#!/usr/bin/env python3
"""ONE PAGE PER NAME: every person the org charts hold, at /people/<slug>.

TJ, 26 October 2026: *"when i search for PEOPLE in the search bar, and i click on them, it
just brings me to the org chart. i am expecting each person gets their own page, with
metadata and then information about their interaction in town that is known."* The search
result promised a person and landed on a chart of eighty.

Writes `fy28/public/data/people.json` (the index: one line per page, and whether a search
engine may index it) and `fy28/public/data/people/<slug>.json` (the page).

WHAT A PAGE HOLDS, and where each part comes from:

- POSITIONS, by year -- `org-charts.json`, the annual reports' rosters FY2011 onward and
  the two staff directories (shown as FY2027, the year they were fetched in). Every year
  links the page it was printed on.
- SERVICE -- per body: the first and last roster that prints the name, how many of that
  body's published rosters print it, and which do not. A roster is a point in time and
  undated within its year, so N printings is at least N-1 years and at most N. A name
  missing from a roster is a name missing from a roster: NOT a departure, a leave or a
  dismissal (rule 7). The edges are marked: a name on the first roster the archive holds
  may have started earlier, and one on the latest may still be there.
- SEATS AND TERMS -- `town-personnel.csv`: elected or appointed, and when the term expires.
- CHAIR -- `board-chairs.csv`, the body's own report naming its chair.
- VOTES -- the town's minutes, `official-votes/`. The minutes print `R. Traikimas`, not a
  person, so the mover is OURS: matched on surname and first initial against the members
  that body's roster prints within a year of the meeting, and left unattributed unless
  exactly one fits.
- NAMED IN THE TOWN'S DOCUMENTS -- a phrase search of the full name in
  `sources/data/minutes-fts.db`, town-published documents only (captions are a finding
  aid, not a record). A LOWER BOUND: minutes mostly print `Mr. Traikimas`.
- CONTACT -- only what the publisher printed: the district's staff directory prints an
  email per person. The town's prints none.
- WHERE THEY SIT -- their latest body's chart for that year, with them in it.

IDENTITY IS THE SLUG. `Scott Barry-Grove` and `Scott Barry Grove` are one page; `Josh
Tocci` and `Joshua Tocci` are two, linked as possibly the same. The same name across two
bodies or two decades is NOT proven to be one person, and the page says so.

EMPLOYEE PAGES ARE NOT INDEXED. TJ, 26 October 2026, reversing the 13 October choice in
build_tenure.py to publish no employee's career: everyone gets a full page, and employee
pages stay out of the sitemap and carry `noindex`. A page is `indexed` when the name holds
or held a public office -- a board seat or an appointed post. Somebody who is both is
indexed, because the office is public.

    python3 scripts/build_people.py
    python3 scripts/build_people.py --check
"""
import argparse
import collections
import csv
import glob
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
ORG = os.path.join(PUB, 'org-charts.json')
OUT_INDEX = os.path.join(PUB, 'people.json')
OUT_DIR = os.path.join(PUB, 'people')
FTS = os.path.join(DATA, 'minutes-fts.db')

PUBLIC_OFFICE = ('board', 'officer')
RECENT_VOTES = 25
RECENT_MENTIONS = 15


def slug_for(name):
    """THE identity. build_search_index.py imports this, so a search result and the page
    it opens can never disagree about who a name is."""
    return re.sub(r'[^a-z0-9]+', '-', ' '.join(name.split()).lower()).strip('-')


def _tokens(name):
    t = [x.strip('.,').lower() for x in name.split()]
    return [x for x in t if x and x not in SUFFIX]


SUFFIX = {'jr', 'sr', 'ii', 'iii', 'iv'}
TITLES = {'mr', 'mrs', 'ms', 'miss', 'dr', 'chair', 'chairman', 'chairwoman', 'chairperson',
          'vice', 'member', 'members', 'clerk', 'selectman', 'selectwoman', 'commissioner',
          'trustee', 'secretary', 'treasurer', 'atty', 'attorney', 'rep', 'councilor'}


def fiscal_year(iso):
    y, m = int(iso[:4]), int(iso[5:7])
    return y + 1 if m >= 7 else y


# ------------------------------------------------------------------------------- inputs

def load_people(org):
    """Every filled row, grouped by slug. Returns {slug: {'names': Counter, 'rows': [...]}}."""
    people = collections.defaultdict(lambda: {'names': collections.Counter(), 'rows': []})
    for r in org['rows']:
        name = ' '.join((r.get('person') or '').split())
        if r.get('status') != 'filled' or not name:
            continue
        s = slug_for(name)
        if not s:
            continue
        people[s]['names'][name] += 1
        people[s]['rows'].append(r)
    return people


def read_csv(name):
    with open(os.path.join(DATA, name), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def seats_by_slug():
    out = collections.defaultdict(list)
    for r in read_csv('town-personnel.csv'):
        if (r.get('person') or '').strip():
            out[slug_for(r['person'])].append({
                'fy': r['fy'], 'post': r['post'], 'kind': r['kind'], 'section': r['section'],
                'term_expires': r['term_expires'], 'note': r.get('note') or '', 'page': r['page']})
    return out


def chairs_by_slug():
    out = collections.defaultdict(list)
    for r in read_csv('board-chairs.csv'):
        if (r.get('person') or '').strip():
            out[slug_for(r['person'])].append({'fy': r['fy'], 'body': r['department'],
                                               'title': r['title'], 'page': r['page']})
    return out


def contact_by_slug():
    """Only what the publisher printed. The district prints an email per person; the
    town's directory prints none, so a town employee's page carries no contact line."""
    out = {}
    for r in read_csv('school-staff-directory.csv'):
        if r.get('email') and r.get('person'):
            out.setdefault(slug_for(r['person']), {
                'email': r['email'], 'title': r['title'], 'school': r['school'],
                'fetched': r['fetched'], 'publisher': 'Lunenburg Public Schools staff directory',
                'source_url': r['source']})
    return out


# -------------------------------------------------------------------------------- votes

def parse_mover(s):
    """`R. Traikimas` -> ('r', 'traikimas', None); `RB` -> initials; `John R.` -> first
    name and a surname initial. None when nothing usable is left."""
    s = (s or '').strip()
    if not s or len(s) > 40 or any(c in s for c in ',;/&') or ' and ' in s.lower():
        return None
    raw = [t for t in re.split(r'\s+', s) if t]
    toks = [t for t in raw if t.strip('.').lower() not in TITLES]
    if not toks:
        return None
    if len(toks) == 1:
        t = toks[0].strip('.')
        if re.fullmatch(r'[A-Z]{2,3}', t):
            return ('initials', t[0].lower(), t[-1].lower())
        return ('surname', None, t.lower())
    first, last = toks[0].strip('.').lower(), toks[-1].strip('.').lower()
    if last in SUFFIX and len(toks) > 2:
        last = toks[-2].strip('.').lower()
    if len(last) == 1:
        return ('first+initial', first, last)
    return ('name', first, last)


def matches(parsed, name):
    t = _tokens(name)
    if len(t) < 2:
        return False
    first, last = t[0], t[-1]
    kind, a, b = parsed
    if kind == 'initials':
        return first[0] == a and last[0] == b
    if kind == 'surname':
        return last == b
    if kind == 'first+initial':
        return (first == a or first.startswith(a) or a.startswith(first)) and last[0] == b
    return last == b and (first == a or (len(a) == 1 and first[0] == a) or first.startswith(a)
                          or a.startswith(first))


def attribute_votes(org, people):
    """Every mover and seconder in the town's minutes, matched to one member of that board
    or to nobody. Returns ({slug: [vote...]}, stats)."""
    unit_for_board = collections.defaultdict(set)
    for u in org['units']:
        if (u.get('links') or {}).get('board_slug'):
            unit_for_board[u['links']['board_slug']].add(u['unit'])
    members = collections.defaultdict(lambda: collections.defaultdict(set))  # unit -> fy -> {(slug,name)}
    for s, p in people.items():
        for r in p['rows']:
            members[r['unit']][int(r['fy'])].add((s, ' '.join(r['person'].split())))

    out = collections.defaultdict(list)
    stats = collections.Counter()
    for f in sorted(glob.glob(os.path.join(DATA, 'official-votes', '*', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        units = unit_for_board.get(d['board_slug'])
        fy = fiscal_year(d['meeting_date'])
        for v in d.get('votes', []):
            for role in ('moved_by', 'seconded_by'):
                who = v.get(role)
                if not who:
                    continue
                stats['named'] += 1
                if not units:
                    stats['board not on a chart'] += 1
                    continue
                parsed = parse_mover(who)
                if not parsed:
                    stats['unparseable'] += 1
                    continue
                hit = None
                # The meeting's own fiscal year first; a year either side only if that
                # finds nobody -- a roster printed for FY2020 may lag a seat that began in it.
                for years in ((fy,), (fy - 1, fy + 1)):
                    cand = {s for u in units for y in years for (s, n) in members[u][y]
                            if matches(parsed, n)}
                    if len(cand) == 1:
                        hit = cand.pop()
                        break
                    if len(cand) > 1:
                        break
                if not hit:
                    stats['no single member fits'] += 1
                    continue
                stats['attributed'] += 1
                out[hit].append({
                    'date': d['meeting_date'], 'board_slug': d['board_slug'],
                    'role': 'moved' if role == 'moved_by' else 'seconded',
                    'as_printed': who, 'motion': v.get('motion') or '',
                    'outcome': v.get('outcome') or '', 'procedural': bool(v.get('procedural')),
                    'url': d['source'].get('doc_url') or d['source'].get('minutes_url')})
    return out, stats


# ----------------------------------------------------------------------------- mentions

def mentions(people):
    """Town-published documents whose text contains the full name as a phrase."""
    if not os.path.exists(FTS):
        sys.exit('build_people: %s is missing. Run scripts/build_minutes_fts.py first -- a '
                 'page saying nobody named this person must not come from an absent index.' % FTS)
    db = sqlite3.connect('file:%s?mode=ro' % FTS, uri=True)
    total = db.execute("SELECT COUNT(*) FROM doc WHERE corpus='document'").fetchone()[0]
    out = {}
    for s, p in people.items():
        name = p['names'].most_common(1)[0][0]
        toks = [t for t in re.split(r'[^A-Za-z0-9]+', name) if t]
        if len(toks) < 2:
            continue
        phrase = '"%s"' % ' '.join(toks)
        # The match first, then the rows by rowid. Written as one JOIN the planner walks
        # `doc` instead, and the run took eight minutes rather than seconds.
        ids = [r[0] for r in db.execute("SELECT rowid FROM fts WHERE fts MATCH ?", (phrase,))]
        if not ids:
            continue
        rows = db.execute(
            "SELECT DISTINCT doc_key, board, board_slug, date, kind, cite_url FROM doc "
            "WHERE rowid IN (%s) AND corpus = 'document' ORDER BY date DESC"
            % ','.join('?' * len(ids)), ids).fetchall()
        seen, docs = set(), []
        for k, board, bslug, date, kind, url in rows:
            if k in seen:
                continue
            seen.add(k)
            docs.append({'board': board, 'board_slug': bslug, 'date': date, 'kind': kind, 'url': url})
        if docs:
            out[s] = docs
    return out, total


# -------------------------------------------------------------------------------- build

def build():
    org = json.load(open(ORG, encoding='utf-8'))
    people = load_people(org)
    unit_meta = {u['unit']: u for u in org['units']}
    sources = org['sources']
    seats, chairs, contact = seats_by_slug(), chairs_by_slug(), contact_by_slug()
    # The annual report for each year, read off the chart's own sources, so a seat or a
    # chair links the page it was printed on. `page` in both CSVs is the PDF page.
    report = {}
    for k, v in sources.items():
        if 'town-annual-reports' in (v.get('copy_url') or ''):
            report.setdefault(k.split('|')[0], v['copy_url'].split('#')[0])
    for group in (seats, chairs):
        for xs in group.values():
            for x in xs:
                x['url'] = ('%s#page=%s' % (report[x['fy']], x['page'])
                            if x['fy'] in report and x['page'] else None)
    votes, vstats = attribute_votes(org, people)
    board_name = {b['slug']: b['name'] for b in
                  json.load(open(os.path.join(PUB, 'boards-nav.json'), encoding='utf-8'))['boards']}
    named, corpus = mentions(people)

    rows_by_unit_fy = collections.defaultdict(list)
    for r in org['rows']:
        rows_by_unit_fy[(r['unit'], r['fy'])].append(r)

    # Possibly the same person, another slug: same body, surname and first initial; or the
    # same first name and surname in any body.
    by_key = collections.defaultdict(set)
    for s, p in people.items():
        for r in p['rows']:
            t = _tokens(r['person'])
            if len(t) >= 2:
                by_key[(r['unit'], t[-1], t[0][0])].add(s)
                # A middle initial printed one year and not the next: anywhere in town.
                by_key[('*', t[-1], t[0])].add(s)

    index, pages = [], {}
    for s, p in sorted(people.items()):
        name = p['names'].most_common(1)[0][0]
        rows = sorted(p['rows'], key=lambda r: (r['fy'], r['unit']))
        kinds = sorted({r['unit_kind'] for r in rows})
        latest = max(rows, key=lambda r: (r['fy'], -int(r.get('tier') or 0)))

        positions = collections.OrderedDict()
        for r in rows:
            k = (r['unit'], r.get('subunit') or '', r['role'] or 'listed')
            src = sources.get('%s|%s' % (r['fy'], r['source'])) or {}
            positions.setdefault(k, []).append({'fy': r['fy'], 'url': src.get('copy_url'),
                                                'label': src.get('label') or r['source'],
                                                'section': r.get('section') or ''})
        pos_out = [{'unit': u, 'subunit': su, 'role': role,
                    'unit_kind': unit_meta.get(u, {}).get('kind', ''),
                    'years': sorted({y['fy']: y for y in ys}.values(), key=lambda y: y['fy'])}
                   for (u, su, role), ys in positions.items()]
        pos_out.sort(key=lambda x: max(y['fy'] for y in x['years']), reverse=True)

        service = []
        for u in sorted({r['unit'] for r in rows}):
            published = [y for y in unit_meta[u]['years']]
            printed = sorted({r['fy'] for r in rows if r['unit'] == u})
            first, last = printed[0], printed[-1]
            inside = [y for y in published if first <= y <= last]
            service.append({
                'unit': u, 'unit_kind': unit_meta[u]['kind'],
                'published': published, 'printed': printed,
                'first': first, 'last': last,
                'not_printed_inside': [y for y in inside if y not in printed],
                'rosters_inside': len(inside),
                'before_archive': first == published[0],
                'on_latest': last == published[-1],
                'chart_url': '/org-charts?unit=%s&fy=%s&person=%s' % (
                    _q(u), last, _q(name))})
        service.sort(key=lambda x: x['last'], reverse=True)

        # Where they sit: the latest body's chart that year, inside their building if a school.
        scope = [r for r in rows_by_unit_fy[(latest['unit'], latest['fy'])]
                 if (latest.get('subunit') or '') == (r.get('subunit') or '')]
        if len(scope) > 30:
            shown = [r for r in scope if r['tier'] in ('0', '1', '2')
                     or slug_for(r['person'] or '') == s]
        else:
            shown = scope
        sit = {
            'unit': latest['unit'], 'subunit': latest.get('subunit') or '', 'fy': latest['fy'],
            'total': len(scope),
            'rows': [{'person': ' '.join((r['person'] or '').split()), 'role': r['role'],
                      'tier': r['tier'], 'status': r['status'],
                      'slug': slug_for(r['person']) if r['person'] and r['status'] == 'filled' else '',
                      'me': slug_for(r['person'] or '') == s}
                     for r in sorted(shown, key=lambda r: (r['tier'], r['role'] or '', r['person'] or ''))],
            'others_by_tier': dict(collections.Counter(r['tier'] for r in scope if r not in shown)),
            'chart_url': '/org-charts?unit=%s&fy=%s&person=%s' % (_q(latest['unit']), latest['fy'], _q(name)),
        }

        v = sorted(votes.get(s, []), key=lambda x: x['date'], reverse=True)
        by_board = collections.OrderedDict()
        for x in v:
            x['board'] = board_name.get(x['board_slug'], x['board_slug'])
            b = by_board.setdefault(x['board_slug'], {'board_slug': x['board_slug'],
                                                     'board': x['board'], 'moved': 0,
                                                     'seconded': 0, 'meetings': set(),
                                                     'first': x['date'], 'last': x['date']})
            b[x['role']] += 1
            b['meetings'].add(x['date'])
            b['first'] = min(b['first'], x['date'])
        vote_out = None
        if v:
            vote_out = {
                'moved': sum(1 for x in v if x['role'] == 'moved'),
                'seconded': sum(1 for x in v if x['role'] == 'seconded'),
                'meetings': len({(x['board_slug'], x['date']) for x in v}),
                'as_printed': sorted({x['as_printed'] for x in v}),
                'by_board': [dict(b, meetings=len(b['meetings'])) for b in by_board.values()],
                'recent': v[:RECENT_VOTES]}

        docs = named.get(s, [])
        aliases = set()
        for r in rows:
            t = _tokens(r['person'])
            if len(t) >= 2:
                aliases |= by_key[(r['unit'], t[-1], t[0][0])] | by_key[('*', t[-1], t[0])]
        aliases.discard(s)

        indexed = any(k in PUBLIC_OFFICE for k in kinds)
        page = {
            'generated_by': 'scripts/build_people.py',
            'slug': s, 'name': name,
            'spellings': sorted(p['names']) if len(p['names']) > 1 else [],
            'indexed': indexed,
            'kinds': kinds,
            'latest': {'fy': latest['fy'], 'role': latest['role'], 'unit': latest['unit'],
                       'subunit': latest.get('subunit') or '', 'unit_kind': latest['unit_kind'],
                       'directory': latest['fy'] == '2027'},
            'contact': contact.get(s),
            'positions': pos_out,
            'service': service,
            'seats': sorted(seats.get(s, []), key=lambda x: x['fy'], reverse=True),
            'chairs': sorted(chairs.get(s, []), key=lambda x: x['fy'], reverse=True),
            'votes': vote_out,
            'named': {'count': len(docs), 'corpus': corpus,
                      'first': docs[-1]['date'] if docs else None,
                      'last': docs[0]['date'] if docs else None,
                      'recent': docs[:RECENT_MENTIONS]},
            'sits': sit,
            'possibly_same': sorted(aliases),
        }
        pages[s] = page
        index.append({'slug': s, 'name': name, 'indexed': indexed, 'kinds': kinds,
                      'role': latest['role'], 'unit': latest['unit'], 'fy': latest['fy']})

    # Names for the cross-links, so a page never shows a bare slug.
    names = {x['slug']: x['name'] for x in index}
    printed_in = collections.defaultdict(set)  # (slug, unit) -> {fy}
    for s, p in people.items():
        for r in p['rows']:
            printed_in[(s, r['unit'])].add(r['fy'])
    for page in pages.values():
        # A YEAR PRINTED UNDER THE OTHER SPELLING IS NOT AN EMPTY YEAR. `Timothy Santry`
        # has a hole from FY2017 to FY2022 that `Tim Santry` fills; drawn empty, the strip
        # reads as six years away. Marked as the other spelling, never merged.
        for sv in page['service']:
            other = {}
            for a in page['possibly_same']:
                for fy in printed_in[(a, sv['unit'])]:
                    if fy not in sv['printed']:
                        other.setdefault(fy, names[a])
            sv['printed_as_other'] = dict(sorted(other.items()))
        page['possibly_same'] = [{'slug': a, 'name': names[a]} for a in page['possibly_same']]

    idx = {'generated_by': 'scripts/build_people.py',
           'about': 'One page per name the org charts hold. `indexed` is false for employees: '
                    'their pages carry noindex and are not in the sitemap.',
           'counts': {'people': len(index), 'indexed': sum(x['indexed'] for x in index),
                      'votes_named': vstats['named'], 'votes_attributed': vstats['attributed'],
                      'documents_searched': corpus},
           'people': index}
    return idx, pages, vstats


def _q(s):
    from urllib.parse import quote
    return quote(s, safe='')


def dump(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'), sort_keys=False) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    idx, pages, vstats = build()

    want = {OUT_INDEX: dump(idx)}
    want.update({os.path.join(OUT_DIR, s + '.json'): dump(p) for s, p in pages.items()})
    have = set(glob.glob(os.path.join(OUT_DIR, '*.json')))
    if args.check:
        stale = [k for k, v in want.items()
                 if not os.path.exists(k) or open(k, encoding='utf-8').read() != v]
        extra = have - set(want)
        if stale or extra:
            print('build_people: %d stale, %d no longer a person. Run scripts/build_people.py'
                  % (len(stale), len(extra)))
            for k in (stale + sorted(extra))[:10]:
                print('   ', os.path.relpath(k, ROOT))
            sys.exit(1)
        print('build_people: %d pages reproduce.' % len(pages))
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    for k, v in want.items():
        tmp = k + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(v)
        os.replace(tmp, k)
    for k in have - set(want):
        os.remove(k)
    c = idx['counts']
    print('build_people: %d pages, %d indexed (public office), %d noindex (employees).'
          % (c['people'], c['indexed'], c['people'] - c['indexed']))
    print('  votes: %d movers and seconders named in the minutes, %d attributed to one member '
          '(%.0f%%)' % (vstats['named'], vstats['attributed'],
                        100.0 * vstats['attributed'] / max(1, vstats['named'])))
    for k in ('board not on a chart', 'unparseable', 'no single member fits'):
        print('    %-24s %d' % (k, vstats[k]))
    print('  named in town documents: %d of %d pages, searched %d documents'
          % (sum(1 for p in pages.values() if p['named']['count']), len(pages), c['documents_searched']))


if __name__ == '__main__':
    main()
