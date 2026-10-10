#!/usr/bin/env python3
"""EVERY JOB POSTING WE WATCH -- the town's and the school district's -- as one page.

    python3 scripts/build_job_postings.py [--check]

TJ, 10 October 2026: *"make sure the boards and department pages have a JOB POSTINGS page
linked for any jobs available. And a history on that same page of openings and fills."*

Two employers, two sources, one page:

  * THE SCHOOL DISTRICT, on SchoolSpring. Already extracted by
    `extract_school_job_postings.py` into `school-job-postings.csv` and
    `school-job-posting-changes.csv`; this reads those two and re-derives nothing.
  * THE TOWN, on its own job board, snapshotted by `fetch_town_job_postings.py`. This file
    is that source's extractor, and writes `town-job-postings.csv` and
    `town-job-posting-changes.csv` from the snapshots and the log of every look, in the same
    shape and with the same date rules as the school side.

And `fy28/public/data/job-postings.json`, which `/jobs` draws and which every board and
department page reads to decide whether it links there. ONE PASS, so the page, the links
and the tables cannot disagree (rule 7d).

WHO A POSTING BELONGS TO is `sources/data/job-posting-owners.csv`, curated and OURS: the
town prints a department name (`Department: Assessor`) and the site's pages are keyed by
board and department slugs, and the join between the two is a judgement with a stated
basis. A posting whose department is not in that file is still on `/jobs` -- it is never
dropped -- and the build prints it, so the file gets a row rather than the posting a
silent absence.

TAKEN DOWN, NOT FILLED (rule 7). A posting leaving the listing is observed. Why it left --
hired, closed, withdrawn, reposted -- is not, on either site. Every label here says taken
down, and the page says once, beside the history, what that does and does not mean.

WHAT EACH DATE MEANS. `first_seen` / `last_seen` / `removed_seen` are days WE LOOKED; the
posted date is the publisher's. Same rules as the school extractor's docstring, which is
the long version.
"""
import argparse
import csv
import datetime
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import fetch_town_job_postings as T  # noqa: E402

DATA = os.path.join(ROOT, 'sources', 'data')
OWNERS_CSV = os.path.join(DATA, 'job-posting-owners.csv')
SCHOOL_ROWS = os.path.join(DATA, 'school-job-postings.csv')
SCHOOL_EVENTS = os.path.join(DATA, 'school-job-posting-changes.csv')
TOWN_ROWS = os.path.join(DATA, 'town-job-postings.csv')
TOWN_EVENTS = os.path.join(DATA, 'town-job-posting-changes.csv')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'job-postings.json')
BOARDS_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'boards.json')
FINANCE_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'finance.json')
SCHOOL_DOCS = os.path.join(ROOT, 'sources', 'district-budget', 'docs', 'personnel', 'job-postings')

TOWN_SITE = 'https://www.lunenburgma.gov'
TOWN_COLS = ['posting_id', 'title', 'department_as_printed', 'category', 'posted_date',
             'posted_as_printed', 'closing_as_printed', 'status', 'first_seen', 'last_seen',
             'removed_seen', 'looks_listed', 'gaps', 'url', 'listing_file']
TOWN_CHANGE_COLS = ['date', 'prev_look', 'posting_id', 'event', 'field', 'before', 'after',
                    'title', 'department_as_printed', 'posted_date', 'source_file']
TOWN_FIELDS = [('title', 'title'), ('department_as_printed', 'department'),
               ('category', 'category'), ('posted_as_printed', 'posted date'),
               ('closing_as_printed', 'closing terms'), ('summary', 'summary')]

EMPLOYERS = {
    'town': {'name': 'Town of Lunenburg', 'where': 'the town’s own job board',
             'url': T.URL},
    'schools': {'name': 'Lunenburg Public Schools', 'where': 'SchoolSpring',
                'url': 'https://www.schoolspring.com/jobs?organization=e-11047'},
}


# ------------------------------------------------------------------------- the town side

def town_looks(snaps):
    """[(date, snapshot)] -- the school extractor's rule, on the town's log."""
    by_day = {}
    p = os.path.join(T.DOCS, 'checked.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            snap = r.get('snapshot') or ''
            if snap not in snaps or 'waits' in (r.get('note') or ''):
                continue
            by_day[r['checked']] = snap
    for s in snaps:
        by_day.setdefault(s, s)
    return sorted(by_day.items())


def iso_posted(printed):
    """`September 4, 2026 10:00 AM` -> `2026-09-04`; '' if the town printed something else."""
    try:
        return datetime.datetime.strptime(printed.split(' ', 3)[0] + ' ' + ' '.join(printed.split(' ')[1:3]),
                                          '%B %d, %Y').date().isoformat()
    except (ValueError, IndexError):
        return ''


def town_listing(snap):
    blob = open(os.path.join(T.DOCS, snap, 'listing.html'), 'rb').read()
    return {j['job_id']: j for j in T.parse(blob)}


def build_town():
    snaps = T.snapshot_log.snapshots(T.DOCS)
    if not snaps:
        return [], [], []
    lk = town_looks(snaps)
    cache = {s: town_listing(s) for s in {s for _, s in lk}}
    dates = [d for d, _ in lk]
    seen, last = {}, {}
    for date, snap in lk:
        for i, j in cache[snap].items():
            seen.setdefault(i, []).append(date)
            last[i] = (j, snap)
    rows = []
    for i in sorted(seen, key=lambda x: (seen[x][0], int(x))):
        ds = seen[i]
        j, snap = last[i]
        removed = '' if ds[-1] == dates[-1] else next(d for d in dates if d > ds[-1])
        rows.append({
            'posting_id': i, 'title': j['title'],
            'department_as_printed': j['department_as_printed'], 'category': j['category'],
            'posted_date': iso_posted(j['posted_as_printed']),
            'posted_as_printed': j['posted_as_printed'],
            'closing_as_printed': j['closing_as_printed'],
            'status': 'removed' if removed else 'open',
            'first_seen': ds[0], 'last_seen': ds[-1], 'removed_seen': removed,
            'looks_listed': str(len(ds)),
            'gaps': str(len([d for d in dates if ds[0] <= d <= ds[-1]]) - len(ds)),
            'url': TOWN_SITE + j['href'],
            'listing_file': 'sources/%s/%s/listing.html' % (T.REL, snap),
        })
    events, prev, present, prev_date = [], {}, set(), ''
    for date, snap in lk:
        now = cache[snap]
        src = 'sources/%s/%s/listing.html' % (T.REL, snap)
        for i in sorted(now, key=int):
            j = now[i]
            base = {'date': date, 'prev_look': prev_date, 'posting_id': i, 'title': j['title'],
                    'department_as_printed': j['department_as_printed'],
                    'posted_date': iso_posted(j['posted_as_printed']), 'source_file': src,
                    'field': '', 'before': '', 'after': ''}
            if i not in prev:
                events.append(dict(base, event='posted'))
            elif i not in present:
                events.append(dict(base, event='relisted'))
            if i in prev:
                for f, _ in TOWN_FIELDS:
                    if prev[i][f] != j[f]:
                        events.append(dict(base, event='edited', field=f, before=prev[i][f], after=j[f]))
            prev[i] = j
        for i in sorted(present - set(now), key=int):
            j = prev[i]
            events.append({'date': date, 'prev_look': prev_date, 'posting_id': i,
                           'event': 'removed', 'field': '', 'before': '', 'after': '',
                           'title': j['title'], 'department_as_printed': j['department_as_printed'],
                           'posted_date': iso_posted(j['posted_as_printed']), 'source_file': src})
        present, prev_date = set(now), date
    order = {'posted': 0, 'relisted': 1, 'edited': 2, 'removed': 3}
    events.sort(key=lambda e: (e['date'], order[e['event']], int(e['posting_id'])))
    return rows, events, lk


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n')
    w.writeheader()
    w.writerows({k: r.get(k, '') for k in cols} for r in rows)
    return buf.getvalue()


# ----------------------------------------------------------------------------- the owners

def owners():
    """{(employer, department_as_printed): owner dict} from the curated file, each owner
    named and addressed off the site's own payloads -- a slug that names no page fails."""
    names = {}
    for b in json.load(open(BOARDS_JSON, encoding='utf-8'))['boards']:
        names[('board', b['slug'])] = (b['name'], '/boards/' + b['slug'])
    for d in json.load(open(FINANCE_JSON, encoding='utf-8'))['departments']:
        if d['kind'] == 'department':
            names[('department', d['slug'])] = (d['name'], '/departments/' + d['slug'])
    out = {}
    for r in csv.DictReader(open(OWNERS_CSV, encoding='utf-8')):
        key = (r['owner_kind'], r['owner_slug'])
        if key not in names:
            raise SystemExit('job-posting-owners.csv names %s %r, and no such page exists'
                             % key)
        name, href = names[key]
        out[(r['employer'], r['department_as_printed'])] = {
            'kind': r['owner_kind'], 'slug': r['owner_slug'], 'name': name, 'href': href,
            'basis': r['basis']}
    return out


def owner_of(own, employer, dept):
    return own.get((employer, dept)) or own.get((employer, ''))


# ---------------------------------------------------------------------------- the payload

def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%B'), d.year)


def school_looks():
    p = os.path.join(SCHOOL_DOCS, 'checked.csv')
    return sorted({r['checked'] for r in csv.DictReader(open(p, encoding='utf-8')) if r.get('snapshot')})


def build_payload(town_rows, town_events, town_lk):
    own = owners()
    school_rows = list(csv.DictReader(open(SCHOOL_ROWS, encoding='utf-8')))
    school_events = list(csv.DictReader(open(SCHOOL_EVENTS, encoding='utf-8')))
    labels = dict(TOWN_FIELDS + [('closing_date', 'closing date'), ('posted_date', 'posted date'),
                                 ('display_date', 'display date'), ('description', 'description'),
                                 ('requirements', 'requirements'), ('pay', 'pay'),
                                 ('locations', 'locations'), ('school', 'school'),
                                 ('positions', 'positions'), ('job_type', 'job type')])
    unmatched = set()

    def owner(employer, dept, title):
        o = owner_of(own, employer, dept)
        if not o:
            unmatched.add('%s: %s (%s)' % (employer, dept or '(no department printed)', title))
        return o

    active, history = [], []
    for r in school_rows:
        o = owner('schools', '', r['title'])
        if r['status'] == 'open':
            active.append({'employer': 'schools', 'id': r['posting_id'], 'title': r['title'],
                           'department': r['locations'].split(' | ')[0] if r['locations'] else '',
                           'posted': r['posted_date'], 'closes': r['closing_date'],
                           'closing_as_printed': '', 'job_type': r['job_type'],
                           'positions': r['positions'], 'url': r['url'],
                           'source': '/docs/' + r['detail_file'][len('sources/'):],
                           'first_seen': r['first_seen'], 'owner': o['slug'] if o else ''})
    for e in school_events:
        o = owner('schools', '', e['title'])
        h = {'employer': 'schools', 'date': e['date'], 'prev_look': e['prev_look'],
             'id': e['posting_id'], 'event': e['event'], 'title': e['title'],
             'posted': e['posted_date'], 'owner': o['slug'] if o else '',
             'source': '/docs/' + e['source_file'][len('sources/'):]}
        if e['event'] == 'edited':
            h['field'] = labels.get(e['field'], e['field'])
            if e['field'] not in ('description', 'requirements'):
                h['before'], h['after'] = e['before'], e['after']
        history.append(h)
    for r in town_rows:
        o = owner('town', r['department_as_printed'], r['title'])
        if r['status'] == 'open':
            active.append({'employer': 'town', 'id': r['posting_id'], 'title': r['title'],
                           'department': r['department_as_printed'],
                           'posted': r['posted_date'], 'closes': '',
                           'closing_as_printed': r['closing_as_printed'], 'job_type': r['category'],
                           'positions': '', 'url': r['url'],
                           'source': '/docs/' + r['listing_file'][len('sources/'):],
                           'first_seen': r['first_seen'], 'owner': o['slug'] if o else ''})
    for e in town_events:
        o = owner('town', e['department_as_printed'], e['title'])
        h = {'employer': 'town', 'date': e['date'], 'prev_look': e['prev_look'],
             'id': e['posting_id'], 'event': e['event'], 'title': e['title'],
             'posted': e['posted_date'], 'owner': o['slug'] if o else '',
             'source': '/docs/' + e['source_file'][len('sources/'):]}
        if e['event'] == 'edited':
            h['field'] = labels.get(e['field'], e['field'])
            if e['field'] != 'summary':
                h['before'], h['after'] = e['before'], e['after']
        history.append(h)
    active.sort(key=lambda a: (a['posted'], a['employer'], a['id']), reverse=True)
    order = {'posted': 0, 'relisted': 1, 'edited': 2, 'removed': 3}
    history.sort(key=lambda h: (h['date'], -order[h['event']], h['employer'], h['id']), reverse=True)

    school_dates = school_looks()
    emp = []
    for key, rows, looks_ in (('town', town_rows, [d for d, _ in town_lk]),
                              ('schools', school_rows, school_dates)):
        if not looks_:
            continue
        emp.append(dict(EMPLOYERS[key], id=key,
                        tracking_since=looks_[0], tracking_since_text=long_date(looks_[0]),
                        as_of=looks_[-1], looks=len(looks_),
                        open=sum(r['status'] == 'open' for r in rows), seen=len(rows),
                        taken_down=sum(r['status'] == 'removed' for r in rows)))
    by_owner = {}
    for o in own.values():
        by_owner.setdefault(o['slug'], {'name': o['name'], 'href': o['href'], 'kind': o['kind'],
                                        'basis': o['basis'], 'open': 0, 'seen': 0})
    for a in active:
        if a['owner']:
            by_owner[a['owner']]['open'] += 1
    for h in history:
        if h['owner'] and h['event'] in ('posted',):
            by_owner[h['owner']]['seen'] += 1
    as_of = max(e['as_of'] for e in emp)
    return {
        'as_of': as_of, 'as_of_text': long_date(as_of),
        'employers': emp,
        'owners': by_owner,
        'active': active,
        'history': history,
        'unmatched': sorted(unmatched),
        'grain': ('Postings, as each employer lists them, checked once a day: the Town of '
                  'Lunenburg on its own job board and Lunenburg Public Schools on SchoolSpring. '
                  'A posting is one advertisement, not one vacancy, and one leaving the list is '
                  'not one being filled.'),
        'sources': [
            {'label': 'The town’s job board', 'url': T.URL},
            {'label': 'The district’s postings on SchoolSpring', 'url': EMPLOYERS['schools']['url']},
            {'label': 'Our table of the town’s postings', 'url': '/docs/data/town-job-postings.csv'},
            {'label': 'Our log of every change to them', 'url': '/docs/data/town-job-posting-changes.csv'},
            {'label': 'Our table of the district’s postings', 'url': '/docs/data/school-job-postings.csv'},
            {'label': 'Our log of every change to them', 'url': '/docs/data/school-job-posting-changes.csv'},
            {'label': 'Which board or department each posting is linked to, and why (ours)',
             'url': '/docs/data/job-posting-owners.csv'},
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, events, lk = build_town()
    payload = build_payload(rows, events, lk)
    outs = [(TOWN_ROWS, csv_text(TOWN_COLS, rows)),
            (TOWN_EVENTS, csv_text(TOWN_CHANGE_COLS, events)),
            (PAYLOAD, json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + '\n')]
    for u in payload['unmatched']:
        print('  NOTE: no board or department for %s -- on /jobs, linked from no page; '
              'add a row to sources/data/job-posting-owners.csv' % u)
    if a.check:
        bad = 0
        for path, want in outs:
            have = open(path, encoding='utf-8', newline='').read() if os.path.exists(path) else None
            if have != want:
                print('STALE -- %s; run scripts/build_job_postings.py' % os.path.relpath(path, ROOT))
                bad = 1
        if not bad:
            print('ok -- %d open posting(s) across %d employer(s); every output reproduces'
                  % (len(payload['active']), len(payload['employers'])))
        return bad
    for path, want in outs:
        tmp = path + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='').write(want)
        os.replace(tmp, path)
    for e in payload['employers']:
        print('%s: %d open, %d seen, %d taken down, %d look(s) since %s'
              % (e['name'], e['open'], e['seen'], e['taken_down'], e['looks'], e['tracking_since']))
    print('wrote %s, %s, %s' % tuple(os.path.relpath(p, ROOT) for p, _ in outs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
