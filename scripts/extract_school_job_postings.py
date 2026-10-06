#!/usr/bin/env python3
"""THE DISTRICT'S JOB POSTINGS AS A HISTORY: every posting ever listed, when we saw it, and
when we stopped seeing it.

    python3 scripts/extract_school_job_postings.py [--check]

Reads every snapshot `fetch_school_job_postings.py` has written under
`sources/district-budget/docs/personnel/job-postings/`, and the log of every look in its
`checked.csv`, and writes THREE THINGS FROM ONE PASS (rule 7d), so they cannot disagree:

  * `sources/data/school-job-postings.csv` -- ONE ROW PER POSTING, keyed on SchoolSpring's
    own job id, which the system issues and never reuses;
  * `sources/data/school-job-posting-changes.csv` -- ONE ROW PER EVENT: posted, edited (one
    row per field, before and after; descriptions compared as text, whitespace ignored),
    relisted, removed;
  * `fy28/public/data/school-job-postings.json` -- what the School Committee page draws.

TJ, 5 October 2026: *"see if new job postings are added or some removed... and keep the
history as a table."*

WHAT EACH DATE MEANS, AND WHAT IT DOES NOT (rule 7 -- a proxy is not a fact).

  * `first_seen`   -- the first day WE LOOKED and the posting was listed. It is NOT the day
                      the district posted it; it is bounded by our fetch cadence, and for
                      every posting already open on the first fetch it is just that date.
  * `last_seen`    -- the last day we looked and it was still listed.
  * `removed_seen` -- the first day we looked and it was GONE. The posting came down at some
                      moment between `last_seen` and `removed_seen`, and nothing here can
                      narrow that further.
  * `posted_date`, `display_date`, `closing_date` -- as SchoolSpring prints them for the
                      posting. These ARE the publisher's dates. `posted_date` and
                      `display_date` differ when a posting was re-dated (the substitute
                      lists were posted 8 July and re-displayed 8 September).

A REMOVAL IS NOT A HIRE. A posting can leave the listing because the post was filled, the
closing date passed, it was withdrawn, or it was reposted under a new id. The data shows
that it left. It does not show why, and `status = removed` means exactly that and no more.
Nor is a posting a vacancy count: `positions` is what the district typed (the substitute
pool says 100), and one posting may cover a pool, a stipend or one FTE.

THE LOOKS COME FROM `checked.csv`, NOT FROM THE SNAPSHOT FOLDERS. Snapshots are written only
when something changed, so the folders alone would make a posting that sat unchanged for
three weeks look as though it were last seen the day it first appeared. Each logged look
names the snapshot it matched, so every look resolves to a listing. A look that was refused
or could not be secured names no snapshot and is not counted as a look at all.

PAY IS PRINTED ONLY WHERE THE DISTRICT SHOWS IT. SchoolSpring carries a `payDisplay` flag;
where it is 0 the figure is hidden on the public page, and it is left blank here too even
when the API returns one -- what the district chose to publish is the publication.

`--check` rebuilds all three in memory and fails unless each reproduces byte for byte.
"""
import argparse
import csv
import datetime
import html
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = 'sources/district-budget/docs/personnel/job-postings'
DOCS = os.path.join(ROOT, REL)
OUT = os.path.join(ROOT, 'sources', 'data', 'school-job-postings.csv')
COLS = ['posting_id', 'title', 'employer_as_printed', 'locations', 'category', 'job_type',
        'positions', 'pay_min', 'pay_max', 'pay_type', 'posted_date', 'display_date',
        'closing_date', 'status', 'first_seen', 'last_seen', 'removed_seen', 'looks_listed',
        'gaps', 'url', 'api_url', 'detail_file']
API = 'https://api.schoolspring.com/api/Jobs/%s?domainName=www.schoolspring.com'
PAGE = 'https://www.schoolspring.com/jobdetail?jobId=%s'


def snapshots():
    import re
    if not os.path.isdir(DOCS):
        return []
    return sorted(d for d in os.listdir(DOCS)
                  if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) and os.path.isdir(os.path.join(DOCS, d)))


def looks(snaps):
    """[(date, snapshot)] -- one per day we looked, the snapshot that day's listing matched."""
    by_day = {}
    p = os.path.join(DOCS, 'checked.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            snap = r.get('snapshot') or ''
            if snap not in snaps:
                continue        # refused, unsecured, or names a snapshot that is not held
            if 'waits' in (r.get('note') or ''):
                continue        # saw a change it could not write: not a look at `snap`
            by_day[r['checked']] = snap     # the last look of a day wins
    for s in snaps:             # a snapshot is always a look on its own day
        by_day.setdefault(s, s)
    return sorted(by_day.items())


def listed(snap):
    """{posting id: listing row} for one snapshot, across every listing page it holds."""
    d = os.path.join(DOCS, snap)
    out = {}
    for f in sorted(os.listdir(d)):
        if f.startswith('listing') and f.endswith('.json'):
            for r in json.load(open(os.path.join(d, f), encoding='utf-8'))['value']['jobsList'] or []:
                out[str(r['jobId'])] = r
    return out


def detail_at(job_id, snap, snaps):
    """The newest held detail for a posting at or before `snap`: (relative path, value)."""
    for s in reversed([x for x in snaps if x <= snap]):
        p = os.path.join(DOCS, s, 'job-%s.json' % job_id)
        if os.path.exists(p):
            return '%s/%s/job-%s.json' % (REL, s, job_id), json.load(open(p, encoding='utf-8'))['value']
    raise SystemExit('posting %s is listed in %s and no detail is held at or before it -- '
                     'run fetch_school_job_postings.py --check' % (job_id, snap))


def category(c):
    """`Category: Subcategory` as SchoolSpring pairs them -- without doubling the category
    where the subcategory already begins with it (`Substitute: Paraprofessional`)."""
    cat, sub = (c.get('category') or '').strip(), (c.get('subCategory') or '').strip()
    if not sub:
        return cat
    return sub if sub.startswith(cat) else '%s: %s' % (cat, sub)


def day(s):
    return (s or '')[:10]


def build():
    snaps = snapshots()
    if not snaps:
        raise SystemExit('no snapshots under %s -- run fetch_school_job_postings.py' % REL)
    lk = looks(snaps)
    seen = {}                                    # id -> [look dates where listed]
    last_row, last_snap = {}, {}
    cache = {}
    for date, snap in lk:
        if snap not in cache:
            cache[snap] = listed(snap)
        for i, r in cache[snap].items():
            seen.setdefault(i, []).append(date)
            last_row[i], last_snap[i] = r, snap
    dates = [d for d, _ in lk]
    latest = dates[-1]
    rows = []
    for i in sorted(seen, key=lambda x: (min(seen[x]), int(x))):
        ds = seen[i]
        first, last = ds[0], ds[-1]
        span = [d for d in dates if first <= d <= last]
        gaps = len(span) - len(ds)
        removed = '' if last == latest else next(d for d in dates if d > last)
        path, v = detail_at(i, last_snap[i], snaps)
        info = v['jobInfo']
        show_pay = info.get('payDisplay') == 1 and (info.get('payMin') or 0) > 0

        def money(x):
            return ('%.2f' % x).rstrip('0').rstrip('.') if show_pay and x else ''
        rows.append({
            'posting_id': i,
            'title': html.unescape(info.get('jobTitle') or last_row[i].get('title') or '').strip(),
            'employer_as_printed': html.unescape(last_row[i].get('employer') or ''),
            'locations': ' | '.join(html.unescape(l.get('locationName') or '')
                                    for l in v.get('jobLocations') or []),
            'category': ' | '.join(category(c) for c in v.get('jobCategories') or []),
            'job_type': info.get('jobTypeName') or '',
            'positions': str(info.get('positions') or ''),
            'pay_min': money(info.get('payMin')),
            'pay_max': money(info.get('payMax')),
            'pay_type': (info.get('payTypeName') or '') if show_pay else '',
            'posted_date': day(info.get('postDate')),
            'display_date': day(info.get('displayDate') or last_row[i].get('displayDate')),
            'closing_date': day(info.get('closeDate') or info.get('applicationDeadline')),
            'status': 'open' if not removed else 'removed',
            'first_seen': first,
            'last_seen': last,
            'removed_seen': removed,
            'looks_listed': str(len(ds)),
            'gaps': str(gaps),
            'url': PAGE % i,
            'api_url': API % i,
            'detail_file': path,
        })
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), rows, lk


# --- THE CHANGE LOG ------------------------------------------------------------------------
#
# One row per EVENT a posting went through, as we saw it: `posted` (first listed), `edited`
# (one row per field that differs between two looks), `relisted` (back after an absence) and
# `removed` (gone). Every event carries `date` -- the look that saw it -- and `prev_look`,
# the look before it, because the change happened somewhere between the two and that window
# is all the data can say. On the first look `prev_look` is empty: a posting already open
# then was not "posted" on that day, only first seen, which is why the printed post date
# travels with the event.

CHANGES = os.path.join(ROOT, 'sources', 'data', 'school-job-posting-changes.csv')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-job-postings.json')
CHANGE_COLS = ['date', 'prev_look', 'posting_id', 'event', 'field', 'before', 'after',
               'title', 'school', 'posted_date', 'source_file']

# WHAT IS COMPARED, in the order a reader cares about it, with the name the page prints.
# Pay is compared AS DISPLAYED: a figure SchoolSpring hides is not published here, so a
# change to a hidden figure is not an event anybody could have seen.
FIELDS = [('title', 'title'), ('school', 'school'), ('locations', 'locations'),
          ('pay', 'pay'), ('closing_date', 'closing date'), ('posted_date', 'posted date'),
          ('display_date', 'display date'), ('positions', 'positions'),
          ('job_type', 'job type'), ('category', 'category'),
          ('description', 'description'), ('requirements', 'requirements')]
LONG = {'description', 'requirements'}


def text_of(s):
    """A posting's description as text a person reads: HTML tags out, entities decoded,
    line breaks kept, runs of blank lines collapsed. Descriptions arrive both as plain text
    with CRLFs and as HTML, so both are brought to the same shape before any comparison."""
    import re
    s = html.unescape(s or '')
    s = re.sub(r'(?i)<\s*br\s*/?>|</\s*(p|div|li|h\d)\s*>', '\n', s)
    s = re.sub(r'(?i)<\s*li[^>]*>', '\n- ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in s.split('\n')]
    out = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return '\n'.join(out).strip()


def same_text(a, b):
    """Equal once whitespace is ignored -- a reflowed paragraph is not an edit."""
    return ' '.join(a.split()) == ' '.join(b.split())


def pay_text(info):
    if not (info.get('payDisplay') == 1 and (info.get('payMin') or 0) > 0):
        return 'not shown'

    def m(x):
        return '${:,.2f}'.format(x).replace('.00', '')
    lo, hi = info.get('payMin') or 0, info.get('payMax') or 0
    rng = m(lo) if not hi or hi == lo else '%s–%s' % (m(lo), m(hi))
    return ('%s %s' % (rng, (info.get('payTypeName') or '').lower())).strip()


def state(listing_row, v):
    """Everything compared about one posting at one look, as the strings the page shows."""
    info = v['jobInfo']
    return {
        'title': html.unescape(info.get('jobTitle') or listing_row.get('title') or '').strip(),
        'school': html.unescape(listing_row.get('employer') or ''),
        'locations': ' | '.join(html.unescape(l.get('locationName') or '')
                                for l in v.get('jobLocations') or []),
        'pay': pay_text(info),
        'closing_date': day(info.get('closeDate') or info.get('applicationDeadline')),
        'posted_date': day(info.get('postDate')),
        'display_date': day(info.get('displayDate') or listing_row.get('displayDate')),
        'positions': str(info.get('positions') or ''),
        'job_type': info.get('jobTypeName') or '',
        'category': ' | '.join(category(c) for c in v.get('jobCategories') or []),
        'description': text_of(info.get('jobDescription')),
        'requirements': text_of(info.get('requirements')),
    }


def build_changes(lk):
    snaps = snapshots()
    cache, events = {}, []
    prev_state, present_before = {}, set()
    prev_date = ''
    for date, snap in lk:
        if snap not in cache:
            cache[snap] = listed(snap)
        now = cache[snap]
        for i in sorted(now, key=int):
            path, v = detail_at(i, snap, snaps)
            st = state(now[i], v)
            base = {'date': date, 'prev_look': prev_date, 'posting_id': i,
                    'title': st['title'], 'school': st['school'],
                    'posted_date': st['posted_date'], 'source_file': path}
            if i not in prev_state:
                events.append(dict(base, event='posted', field='', before='', after=''))
            elif i not in present_before:
                events.append(dict(base, event='relisted', field='', before='', after=''))
            if i in prev_state:
                old = prev_state[i]
                for f, _label in FIELDS:
                    a, b = old[f], st[f]
                    if (same_text(a, b) if f in LONG else a == b):
                        continue
                    events.append(dict(base, event='edited', field=f, before=a, after=b))
            prev_state[i] = st
        for i in sorted(present_before - set(now), key=int):
            st = prev_state[i]
            events.append({'date': date, 'prev_look': prev_date, 'posting_id': i,
                           'event': 'removed', 'field': '', 'before': '', 'after': '',
                           'title': st['title'], 'school': st['school'],
                           'posted_date': st['posted_date'],
                           'source_file': '%s/%s/listing.json' % (REL, snap)})
        present_before = set(now)
        prev_date = date
    order = {'posted': 0, 'relisted': 1, 'edited': 2, 'removed': 3}
    events.sort(key=lambda e: (e['date'], order[e['event']], int(e['posting_id']),
                               [f for f, _ in FIELDS].index(e['field']) if e['field'] else -1))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CHANGE_COLS, lineterminator='\n')
    w.writeheader()
    w.writerows(events)
    return buf.getvalue(), events


def line_diff(a, b):
    """The changed lines of a long text, for a page to show behind an expander."""
    import difflib
    out = []
    for d in difflib.ndiff(a.split('\n'), b.split('\n')):
        if d[:2] in ('- ', '+ ') and d[2:].strip():
            out.append({'op': d[0], 'text': d[2:]})
    return out


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%B'), d.year)


def build_payload(rows, events, lk):
    """What the School Committee page draws, from the same pass as the two CSVs."""
    labels = dict(FIELDS)
    first, latest = lk[0][0], lk[-1][0]
    by_id = {r['posting_id']: r for r in rows}
    active = []
    for r in rows:
        if r['status'] != 'open':
            continue
        _p, v = detail_at(r['posting_id'], latest_snap(lk), snapshots())
        active.append({
            'id': r['posting_id'], 'title': r['title'], 'school': r['employer_as_printed'],
            'posted': r['posted_date'],
            'displayed': r['display_date'] if r['display_date'] != r['posted_date'] else '',
            'closes': r['closing_date'],
            'pay': pay_text(v['jobInfo']) if r['pay_min'] else '',
            'positions': r['positions'], 'job_type': r['job_type'],
            'api_url': r['api_url'], 'page_url': r['url'], 'first_seen': r['first_seen'],
        })
    active.sort(key=lambda a: (a['posted'], a['id']), reverse=True)
    history = []
    for e in events:
        h = {'date': e['date'], 'prev_look': e['prev_look'], 'id': e['posting_id'],
             'event': e['event'], 'title': e['title'], 'school': e['school'],
             'posted': e['posted_date'], 'source': docs_url(e['source_file']),
             'api_url': API % e['posting_id']}
        if e['event'] == 'edited':
            h['field'] = labels[e['field']]
            if e['field'] in LONG:
                h['diff'] = line_diff(e['before'], e['after'])
            else:
                h['before'], h['after'] = e['before'], e['after']
        history.append(h)
    # Newest look first; within a look, the order build_changes fixed.
    days = sorted({h['date'] for h in history}, reverse=True)
    history = [h for d_ in days for h in history if h['date'] == d_]
    n_open = len(active)
    removed = sum(e['event'] == 'removed' for e in events)
    edited = len({(e['date'], e['posting_id']) for e in events if e['event'] == 'edited'})
    return {
        'as_of': latest, 'tracking_since': first, 'tracking_since_text': long_date(first),
        'looks': len(lk),
        'stats': [
            {'value': str(n_open), 'label': 'open postings under the district’s SchoolSpring '
                                             'account, at our last check (%s)' % long_date(latest)},
            {'value': str(len(rows)), 'label': 'postings seen in all since tracking began '
                                               '%s' % long_date(first)},
            {'value': str(removed), 'label': 'postings taken down since then' if removed != 1
                                             else 'posting taken down since then'},
            {'value': str(edited), 'label': 'edits to an open posting seen since then'
                                            if edited != 1 else 'edit to an open posting seen since then'},
        ],
        'grain': grain(rows),
        'active': active,
        'history': history,
        'sources': [
            {'label': 'SchoolSpring job search API, employer e-11047 (what is open)',
             'url': 'https://api.schoolspring.com/api/Jobs/GetPagedJobsWithSearch?domainName='
                    'www.schoolspring.com&keyword=&location=&category=&gradelevel=&jobtype='
                    '&organization=e-11047&swLat=&swLon=&neLat=&neLon=&page=1&size=100'
                    '&sortDateAscending=false'},
            {'label': 'Our table of every posting, one row each',
             'url': '/docs/data/school-job-postings.csv'},
            {'label': 'Our log of every change we saw, one row per event',
             'url': '/docs/data/school-job-posting-changes.csv'},
        ],
    }


def grain(rows):
    """What is counted, with the posting that makes the point named rather than assumed."""
    big = max(rows, key=lambda r: (int(r['positions'] or 0), r['posting_id']))
    return ('Postings on SchoolSpring under the employer account “Lunenburg Public Schools” '
            '(SchoolSpring employer 11047), checked once a day. A posting is one '
            'advertisement, not one vacancy: “%s” is a single posting listing %s positions.'
            % (big['title'], big['positions']))


def docs_url(path):
    """Our held copy of a snapshot file, at the address the site serves it from."""
    return '/docs/' + path[len('sources/'):] if path.startswith('sources/') else path


def latest_snap(lk):
    return lk[-1][1]


def render(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text, rows, lk = build()
    ctext, events = build_changes(lk)
    ptext = render(build_payload(rows, events, lk))
    n_open = sum(r['status'] == 'open' for r in rows)
    outs = [(OUT, text), (CHANGES, ctext), (PAYLOAD, ptext)]
    if a.check:
        bad = 0
        for path, want in outs:
            have = open(path, encoding='utf-8', newline='').read() if os.path.exists(path) else None
            if have != want:
                print('STALE -- %s does not reproduce from the snapshots; run without --check'
                      % os.path.relpath(path, ROOT))
                bad = 1
        if not bad:
            print('ok -- %d postings (%d open, %d removed), %d change event(s), from %d '
                  'look(s); the table, the change log and the page payload all reproduce'
                  % (len(rows), n_open, len(rows) - n_open, len(events), len(lk)))
        return bad
    for path, want in outs:
        open(path, 'w', encoding='utf-8', newline='').write(want)
    print('wrote %s: %d postings (%d open, %d removed) from %d look(s) across %d snapshot(s)'
          % (os.path.relpath(OUT, ROOT), len(rows), n_open, len(rows) - n_open, len(lk),
             len({s for _, s in lk})))
    print('wrote %s: %d event(s)' % (os.path.relpath(CHANGES, ROOT), len(events)))
    print('wrote %s' % os.path.relpath(PAYLOAD, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
