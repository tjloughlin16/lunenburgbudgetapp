#!/usr/bin/env python3
"""What this project holds, counted — for the community, and never typed.

    python3 scripts/build_app_metrics.py            # write the JSON and the one-page markdown
    python3 scripts/build_app_metrics.py --check    # fail if either no longer reproduces

TJ, 11 September 2026: *"generate full app metrics about the data we have ingested and
processed ... something to share with the community to get them intrigued and amazed.
total minutes. total meetings. FYs of data. sources pulled from. anything."*

Every figure here is computed from the archive's own registries -- the manifest, the
meetings index, the transcript index, the analysis database, the published payloads --
on every run. Rule 2: a number typed into a sentence is the one thing here that can be
silently wrong, and a sharing document is the one most likely to be quoted. So the
markdown is generated, and `--check` fails the build the day it drifts.

Rule 3 runs through the layout: what the TOWN and the STATE published is counted apart
from what WE derived. Hours of machine captions are ours; minutes and agendas are the
town's. A reader must be able to tell which is which from the headings alone.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import sqlite3
from collections import Counter
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
MEETINGS = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
DATA = os.path.join(ROOT, 'fy28', 'public', 'data')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
DIST = os.path.join(ROOT, 'fy28', 'dist')
OUT_JSON = os.path.join(DATA, 'app-metrics.json')
OUT_MD = os.path.join(ROOT, 'notes', 'generated', 'APP-METRICS.md')

DOC_EXTS = {'.pdf', '.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt'}


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', errors='replace')))


def metrics(today=None):
    today = today or dt.date.today().isoformat()
    m = {}

    # --- the archive: what somebody else published, and what we hold of it
    man = rows(MANIFEST)
    docs = [r for r in man if os.path.splitext(r['key'])[1].lower() in DOC_EXTS]
    hosts = Counter(urlparse(r['upstream']).netloc for r in man if r.get('upstream'))
    m['archive'] = {
        'files': len(man),
        'gigabytes': round(sum(int(r['bytes']) for r in man) / 1e9, 2),
        'documents': len(docs),                       # PDFs, spreadsheets, Word, PowerPoint
        'documents_by_format': dict(Counter(os.path.splitext(r['key'])[1].lower().lstrip('.') for r in docs).most_common()),
        'source_kinds': sorted({r['key'].split('/')[0] for r in man if '/' in r['key']} - {'data', 'analyses', 'views'}),
        'top_folders': dict(Counter(r['key'].split('/')[0] for r in man).most_common(8)),
        'publisher_sites': len(hosts),
        'publisher_sites_top': dict(hosts.most_common(6)),
        'with_publisher_address': sum(1 for r in man if r.get('upstream')),
    }

    # --- the town's meetings: what it published, and what we captured
    mi = rows(MEETINGS)
    dated = [r for r in mi if r['date'] <= today]
    m['meetings'] = {
        'documents': len(mi),
        'minutes': sum(1 for r in mi if r['kind'] == 'minutes'),
        'agendas': sum(1 for r in mi if r['kind'] == 'agenda'),
        'boards': len({r['board'] for r in mi}),
        'first_date': min(r['date'] for r in dated),
        'last_date': max(r['date'] for r in dated),
        'years': int(max(r['date'] for r in dated)[:4]) - int(min(r['date'] for r in dated)[:4]) + 1,
        'boards_top': dict(Counter(r['board'] for r in mi).most_common(6)),
    }

    # --- recordings: OURS, derived
    ti = [r for r in rows(TRANSCRIPTS) if os.path.exists(os.path.join(ROOT, r['path'])) and r['meeting_date'] <= today]
    secs = sum(int(r.get('seconds') or 0) for r in ti)
    m['recordings'] = {
        'transcribed': len(ti),
        'hours': round(secs / 3600),
        'days_of_audio': round(secs / 86400, 1),
        'boards': len({r['board_slug'] for r in ti}),
        'boards_top': dict(Counter(r['board_slug'] for r in ti).most_common(5)),
        'first_date': min(r['meeting_date'] for r in ti),
        'last_date': max(r['meeting_date'] for r in ti),
    }
    rec = glob.glob(os.path.join(RECORDED, '*', '*.json'))
    votes = transfers = 0
    for f in rec:
        mm = json.load(open(f, encoding='utf-8'))['minutes']
        votes += sum(1 for v in mm['votes'] if not v.get('procedural'))
        transfers += len(mm['transfers'])
    m['our_minutes'] = {'meetings': len(rec), 'substantive_votes': votes, 'transfers': transfers}

    # --- the analysis database: what was extracted and reconciled
    db = sqlite3.connect(DB)
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    total = sum(db.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in tables)

    def count(t):
        return db.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] if t in tables else 0

    def span(t, col='fy'):
        if t not in tables:
            return None
        lo, hi = db.execute('SELECT MIN(%s), MAX(%s) FROM "%s"' % (col, col, t)).fetchone()
        return [lo, hi]

    m['database'] = {
        'tables': len(tables),
        'rows': total,
        'documents_catalogued': count('document'),
        'annual_report_appropriation_lines': count('report_appropriations'),
        'annual_reports_span': span('report_appropriations'),
        'staff_roster_names': count('staff_roster_entries'),
        'staff_roster_span': span('staff_roster_entries'),
        'school_budget_line_years': count('line_history'),
        'school_budget_span': span('line_history'),
        'ledger_lines': count('munis_ledger'),
        'budget_figures': count('budget_figure'),
        'dese_tables': sum(1 for t in tables if t.startswith('dese_')),
        'cuts_announced_in_writing': count('stated_cuts'),
        'rates_in_the_model': count('rate_register'),
        'placement_count_years': count('placement_counts'),
        'grant_awards': count('grant_award'),
    }

    # --- what we wrote: analyses, conclusions, gaps, posts
    conclusions = 0
    for f in glob.glob(os.path.join(DATA, '*.json')):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict):
            conclusions += len(d.get('conclusions', []) or [])
    reports = json.load(open(os.path.join(DATA, 'reports.json'), encoding='utf-8'))
    blog = json.load(open(os.path.join(DATA, 'blog.json'), encoding='utf-8'))
    pages = len(glob.glob(os.path.join(DIST, '*.html'))) + len(glob.glob(os.path.join(DIST, '*', '*.html'))) if os.path.isdir(DIST) else None
    m['written'] = {
        'analyses': len(reports.get('reports', reports) if isinstance(reports, dict) else reports),
        'conclusions_published': conclusions,
        'registered_gaps': len(rows(GAPS)),
        'posts_published': blog.get('counts', {}).get('published'),
        'site_pages': pages,
    }
    m['as_of'] = today
    return m


def fmt(n):
    return '{:,}'.format(n) if isinstance(n, int) else str(n)


def markdown(m):
    a, mt, r, om, d, w = m['archive'], m['meetings'], m['recordings'], m['our_minutes'], m['database'], m['written']
    L = []
    L.append('# The Lunenburg Budget Project, by the numbers')
    L.append('')
    L.append('*As of %s. Every figure below is computed from the archive itself by '
             '`scripts/build_app_metrics.py`; none is typed.*' % m['as_of'])
    L.append('')
    L.append('## What the town and the state published — and we hold')
    L.append('')
    L.append('- **%s documents** — PDFs, spreadsheets, Word files and slide decks — %s files and %s GB in all, '
             'each with its address, its publisher’s filename and a checksum.'
             % (fmt(a['documents']), fmt(a['files']), a['gigabytes']))
    L.append('- **%d kinds of source**: %s.' % (len(a['source_kinds']), ', '.join(a['source_kinds'])))
    L.append('- **%s meeting documents** from **%d town boards**: %s sets of minutes and %s agendas, %s to %s — **%d years**.'
             % (fmt(mt['documents']), mt['boards'], fmt(mt['minutes']), fmt(mt['agendas']), mt['first_date'], mt['last_date'], mt['years']))
    L.append('- **%s annual town report appropriation lines**, FY%s–FY%s, read page by page.'
             % (fmt(d['annual_report_appropriation_lines']), *d['annual_reports_span']))
    L.append('- **%s names** on the town’s printed staff rosters, FY%s–FY%s.'
             % (fmt(d['staff_roster_names']), *d['staff_roster_span']))
    L.append('- **%s school budget line-years**, FY%s–FY%s, and **%s ledger lines** from the town’s own accounting system.'
             % (fmt(d['school_budget_line_years']), *d['school_budget_span'], fmt(d['ledger_lines'])))
    L.append('- **%d state (DESE) data tables** — enrollment, staffing, class size, special education, Chapter 70, per-pupil spending.'
             % d['dese_tables'])
    L.append('')
    L.append('## What we made from it')
    L.append('')
    L.append('- **%s hours of meeting recordings transcribed** — %s meetings, %s days of audio end to end, %s to %s. '
             'Machine captions, ours, a finding aid: they locate a moment; they do not settle what was said.'
             % (fmt(r['hours']), fmt(r['transcribed']), r['days_of_audio'], r['first_date'], r['last_date']))
    L.append('- **%d meetings with our own minutes** written from those recordings — **%d substantive votes** and **%d transfers** logged, each linked to the second of the video.'
             % (om['meetings'], om['substantive_votes'], om['transfers']))
    L.append('- **A database of %s rows in %d tables**, rebuilt from the documents on every run and queryable by anyone at `/api/query`.'
             % (fmt(d['rows']), d['tables']))
    L.append('- **%d analyses** and **%d published conclusions**, every figure recomputed by a script before it ships.'
             % (w['analyses'], w['conclusions_published']))
    L.append('- **%d cuts announced in writing** traced across budget cycles; **%d rates** in the projection, each backtested against the district’s later budgets.'
             % (d['cuts_announced_in_writing'], d['rates_in_the_model']))
    L.append('- **%d registered gaps** — questions the published record cannot answer, each with the one document that would close it.'
             % w['registered_gaps'])
    L.append('- **%s pages** on the site%s.'
             % (fmt(w['site_pages']) if w['site_pages'] else '?',
                (' and **%d posts** on the blog' % w['posts_published']) if w['posts_published'] else ''))
    L.append('')
    L.append('## Where it came from')
    L.append('')
    for host, n in a['publisher_sites_top'].items():
        L.append('- `%s` — %s files' % (host, fmt(n)))
    L.append('')
    L.append('Everything above is checkable: every document is downloadable at its own address, '
             'every figure carries its source, and the whole database is one file anybody can open.')
    L.append('')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    m = metrics()
    js = json.dumps(m, indent=1, ensure_ascii=False) + '\n'
    md = markdown(m)
    if a.check:
        # The date moves daily; compare everything but it.
        def strip(s):
            return '\n'.join(l for l in s.splitlines() if 'as_of' not in l and 'As of ' not in l)
        ok = (os.path.exists(OUT_JSON) and strip(open(OUT_JSON).read()) == strip(js)
              and os.path.exists(OUT_MD) and strip(open(OUT_MD).read()) == strip(md))
        print('ok: app metrics reproduce' if ok else 'STALE: run build_app_metrics.py')
        return 0 if ok else 1
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_JSON, 'w', encoding='utf-8').write(js)
    open(OUT_MD, 'w', encoding='utf-8').write(md)
    print('wrote %s and %s' % (os.path.relpath(OUT_JSON, ROOT), os.path.relpath(OUT_MD, ROOT)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
