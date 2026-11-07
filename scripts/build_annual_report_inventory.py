#!/usr/bin/env python3
"""What we hold from the annual town reports, as one document a person can be sent.

    python3 scripts/build_annual_report_inventory.py          # write the Markdown and the PDF
    python3 scripts/build_annual_report_inventory.py --check  # fail if the Markdown is stale

Writes notes/generated/ANNUAL-REPORT-DATA-INVENTORY.md and, beside it, a PDF printed by
build_analysis_pdf.py --file. It is deliberately NOT under sources/analyses: TJ, 7 November
2026, wanted a PDF to send people, "committed to the repo, but not put as a full report
just yet". So the site does not list it, serve it or put it in the sitemap.

Every count is read from the data when this runs (rule 2): the database for rows and
editions, the report index for the editions held, the page text for pages, the search
index for what search holds. Nothing here is typed. The subject grouping is ours, by table
name, and says so.
"""
import csv
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
DB = os.path.join(DATA, 'lunenburg.db')
SEARCH = os.path.join(DATA, 'search-fts.db')
REPORTS = os.path.join(ROOT, 'sources', 'town-annual-reports')
OUT = os.path.join(ROOT, 'notes', 'generated', 'ANNUAL-REPORT-DATA-INVENTORY.md')
SITE = 'https://lunenburgbudgetproject.org'
GH = 'https://github.com/tjloughlin16/lunenburgbudgetapp/blob/main/'

# Ours: a reading aid, matched on the table name, first match wins.
SUBJECTS = [
    ('About the reports themselves',
     r'annual_report_(catalogue|contents|survey)|report_index|anomal|report_contents|series_coverage|'
     r'report_filing|scan_debris'),
    ('Money: budgets, spending, receipts and debt',
     r'appropriat|payment|receipt|debt|expend|budget|revenue|cash|free_cash|surplus|fund_balance|'
     r'agency_funds|capital|financial|oneoff_finance|warrant_article|vendor|highway_accounts|'
     r'cost|committee_income|energy|revolving|sewer|transitional|special_revenue|treasurer|fee_schedule'),
    ('Taxes, valuation and assessments',
     r'tax|valuation|exemption|new_growth|per_capita|revenue_sharing|state_aid|pie_chart'),
    ('Trust funds and investments', r'trust|investment'),
    ('Pay, staff and officials',
     r'salary|wage|pay_|pay_rates|classification|staff|personnel|roster|official|signature|'
     r'office_hours|meeting_schedules'),
    ('Schools', r'school|enrol|mcas|sped|special_education|student|monty|lunch|placement|teacher|calendar'),
    ('Elections, votes and by-laws', r'election|ballot|bylaw'),
    ('People and vital records', r'vital|burial|births|census|veteran|welfare|nurse|coa_'),
    ('Public safety, permits and services',
     r'fire|police|building|permit|conservation|library|weights|vehicle|cultural|health|town_facts|dept_activity'),
    ('Other lists and one-offs', r'small_one_offs|prose_boxed'),
]
ABOUT_DOCS = 'About the reports themselves'


def edition_key(e):
    m = re.search(r'(\d{4})', e or '')
    return int(m.group(1)) if m else 0


def label(e):
    return e if e.upper().startswith('FY') else e


def first_sentence(s, n=170):
    s = re.sub(r'\s+', ' ', (s or '').replace('|', '/')).strip()
    # A description was written when its table was first built and may date it ("NEW with
    # the 1986 edition", "FY2011-FY2025"); the Years column is computed and is the one to read.
    s = re.sub(r'^NEW with[^:]*:\s*', '', s)
    s = re.sub(r',?\s*\(?(FY)?\d{4}\s*[-–]\s*(FY)?\d{4}\)?', '', s)
    s = s[:1].upper() + s[1:]
    m = re.match(r'(.+?[.;])(\s|$)', s)
    s = m.group(1) if m and len(m.group(1)) > 40 else s
    return s if len(s) <= n else s[:n - 1].rsplit(' ', 1)[0] + '…'


def csv_path(t):
    slug = t.replace('_', '-')
    cands = [os.path.join(DATA, slug + '.csv')]
    if t.startswith('series_'):
        cands.insert(0, os.path.join(DATA, 'report-series', slug[len('series-'):] + '.csv'))
    for p in cands:
        if os.path.exists(p):
            return os.path.relpath(p, ROOT)
    return ''


def tables(db):
    prov = set()
    for r in csv.DictReader(open(os.path.join(DATA, 'dataset-provenance.csv'), encoding='utf-8')):
        if 'annual-town-report' in r['document']:
            prov.add(r['dataset'].replace('-', '_'))
    sem = {r['table_name']: r for r in
           csv.DictReader(open(os.path.join(DATA, 'table-semantics.csv'), encoding='utf-8'))}
    names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    rows = []
    for t in names:
        if not (t.startswith(('report_', 'series_', 'annual_report')) or t in prov):
            continue
        cols = [c[1] for c in db.execute('PRAGMA table_info("%s")' % t)]
        n = db.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
        ycol = next((c for c in ('edition', 'fy', 'report_fy', 'year') if c in cols), None)
        eds = []
        if ycol:
            eds = sorted({str(r[0]) for r in db.execute('SELECT DISTINCT "%s" FROM "%s"' % (ycol, t))
                          if r[0] not in (None, '')}, key=edition_key)
            eds = [e for e in eds if edition_key(e)]
        s = sem.get(t, {})
        subj = next((name for name, pat in SUBJECTS if re.search(pat, t)), 'Other')
        if s.get('role') == 'provenance':
            subj = ABOUT_DOCS
        rows.append(dict(table=t, rows=n, editions=eds, cols=len(cols), subject=subj,
                         paged=any('page' in c for c in cols),
                         what=first_sentence(s.get('what_it_answers') or ''),
                         csv=csv_path(t), series=t.startswith('series_')))
    return rows


def span(eds):
    if not eds:
        return 'not dated'
    a, b = label(eds[0]), label(eds[-1])
    return a if a == b else '%s–%s' % (a, b)


def held_editions():
    out = []
    for r in csv.DictReader(open(os.path.join(REPORTS, 'index.csv'), encoding='utf-8')):
        out.append(r)
    return out


def page_count(index):
    pages, chars = 0, 0
    for r in index:
        p = os.path.join(ROOT, r['text'])
        if os.path.exists(p):
            t = open(p, encoding='utf-8', errors='replace').read()
            pages += len(re.findall(r'^===PAGE \d+===', t, re.M))
            chars += len(t)
    return pages, chars


def search_pages():
    if not os.path.exists(SEARCH):
        return None
    s = sqlite3.connect(SEARCH)
    try:
        return s.execute("SELECT COUNT(*) FROM search WHERE corpus='source' "
                         "AND file_key LIKE '%annual-town-report%'").fetchone()[0]
    except sqlite3.Error:
        return None


def count_csv(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    return sum(1 for _ in csv.DictReader(open(p, encoding='utf-8')))


def fmt(n):
    return '{:,}'.format(n)


def build():
    db = sqlite3.connect(DB)
    T = tables(db)
    index = held_editions()
    years = sorted({edition_key(r['label']) for r in index if edition_key(r['label'])})
    pages, chars = page_count(index)
    sp = search_pages()
    blocked = count_csv('page-blocked.csv')
    data_tables = [t for t in T if t['subject'] != ABOUT_DOCS]
    aid_tables = [t for t in T if t['subject'] == ABOUT_DOCS]
    total_rows = sum(t['rows'] for t in data_tables)
    series = [t for t in data_tables if t['series']]
    pdf_bytes = sum(int(r['bytes'] or 0) for r in index)
    ex = next((t for t in T if t['table'] == 'series_fire_calls'), None) or series[0]

    L = []
    w = L.append
    w('# What we hold from Lunenburg\'s annual town reports')
    w('')
    w('Generated: %s by `scripts/build_annual_report_inventory.py`, from the database and the '
      'archive as they stood that day. Every count below is computed, not typed.'
      % date.today().isoformat())
    w('')
    w('| | |')
    w('|---|---:|')
    w('| Annual reports held, %d to FY%d | %s documents |' % (years[0], years[-1], fmt(len(index))))
    w('| Pages of text read from them | %s pages |' % fmt(pages))
    if sp:
        w('| Pages in the word search | %s pages |' % fmt(sp))
    w('| Tables built from them | %s tables |' % fmt(len(data_tables)))
    w('| Rows in those tables | %s rows |' % fmt(total_rows))
    w('| Of which: year-by-year series | %s tables, %s rows |'
      % (fmt(len(series)), fmt(sum(t['rows'] for t in series))))
    w('| Finding aids about the reports themselves | %s tables |' % fmt(len(aid_tables)))
    w('')
    unpaged = [t['table'] for t in data_tables if not t['paged']]
    w('Rows carry the edition and the page they were printed on, so a number can be checked '
      'against its page%s. The year-by-year series also quote the printed line.'
      % ((' (except %s, which %s across editions)' % (', '.join('`%s`' % u for u in unpaged), 'summarises' if len(unpaged) == 1 else 'summarise'))
         if unpaged else ''))
    w('')

    w('## What you can do with it')
    w('')
    w('- **Search the pages by word.** Any phrase, across %s pages of all %d editions, at '
      '`%s/search`. Each hit links to that page of the original PDF.' % (fmt(sp or pages), len(index), SITE))
    w('- **Ask a question in SQL.** Every table below is in a public database. One web address '
      'runs a read-only query, for example `%s/api/query?sql=SELECT edition, measure, value '
      'FROM %s LIMIT 20`.' % (SITE, ex['table']))
    w('- **Follow a figure back to its page.** Rows carry `edition` and `page`; the original '
      'scanned report is at `%s/docs/town-annual-reports/docs/<file>.pdf#page=N`.' % SITE)
    w('- **Download it.** Every table is a CSV in the public repository (`%s`), named in '
      'the tables below.' % GH.rstrip('/').rsplit('/blob', 1)[0])
    w('- **Compare across 60+ years.** The year-by-year series put the same measure from every '
      'edition in one table: fire calls, burials, enrolment, pay schedules, trust funds, permits.')
    w('')

    w('## How it is stored')
    w('')
    w('1. **The original reports**: %s PDFs (%s MB), kept unchanged in a locked archive, each '
      'with its sha256 and the town\'s own address for it.' % (fmt(len(index)), fmt(pdf_bytes // 1_000_000)))
    w('2. **The page text**: read from every page (by Amazon Textract for the scans), %s MB of '
      'text, one file per report.' % fmt(chars // 1_000_000))
    w('3. **The tables**: CSV files in git, the source of truth. Rows name their page; where '
      'a report prints its own total, the extract is checked against it.')
    w('4. **The database**: the CSVs are loaded into one SQLite database (`lunenburg.db`), '
      'copied online to Cloudflare D1 and queried at `/api/query`.')
    w('5. **The search index**: a second database holding the text of every page with a word '
      'index (SQLite FTS5)%s, searched at `/api/search`.'
      % (', %s annual-report pages' % fmt(sp) if sp else ''))
    w('')
    w('Everything printed in the annual reports is public, names included.')
    w('')

    w('## Every table, by subject')
    w('')
    w('The grouping is ours, made for reading. *Editions* counts the reports a table has rows '
      'from; a series marks the editions that do not print the item in a separate coverage '
      'table.')
    w('')
    order = [name for name, _ in SUBJECTS if name != ABOUT_DOCS] + ['Other']
    for subj in order:
        group = [t for t in data_tables if t['subject'] == subj]
        if not group:
            continue
        w('### %s' % subj)
        w('')
        w('%s tables, %s rows.' % (fmt(len(group)), fmt(sum(t['rows'] for t in group))))
        w('')
        w('| Table | What it holds | Years | Editions | Rows |')
        w('|---|---|---|---:|---:|')
        for t in sorted(group, key=lambda t: -t['rows']):
            w('| `%s` | %s | %s | %d | %s |'
              % (t['table'], t['what'] or '—', span(t['editions']), len(t['editions']), fmt(t['rows'])))
        w('')
        w('CSV files: ' + '; '.join('`%s`' % t['csv'] for t in sorted(group, key=lambda t: t['table'])) + '.')
        w('')

    w('## Finding aids: tables about the reports themselves')
    w('')
    w('These describe the documents rather than the town: what each page holds, which tables '
      'were catalogued, which pages were read and how.')
    w('')
    w('| Table | What it holds | Rows |')
    w('|---|---|---:|')
    for t in sorted(aid_tables, key=lambda t: -t['rows']):
        w('| `%s` | %s | %s |' % (t['table'], t['what'] or '—', fmt(t['rows'])))
    w('')

    w('## What is not in the tables')
    w('')
    if blocked is not None:
        w('- **%s pages are closed as unreadable or printed short**, each registered with its '
          'reason in `sources/data/page-blocked.csv`. Their words, where legible, are still in '
          'search.' % fmt(blocked))
    w('- **Running prose is searchable but not tabulated.** Department narratives, by-law '
      'wording and letters are in the search index and the page text, not in table rows.')
    w('- **Some lists are one row per printed entry** (personnel changes, by-law articles), '
      'not split into columns.')
    w('- **"Not printed" in a series\' coverage** rests partly on text searches rather than '
      'opened pages; each coverage row says which pages were looked at.')
    w('')

    w('## The editions held')
    w('')
    w(', '.join(r['label'].replace(' Annual Town Report', '') for r in
                sorted(index, key=lambda r: (edition_key(r['label']), r['label']))) + '.')
    w('')
    return '\n'.join(L) + '\n'


def main():
    md = build()
    if '--check' in sys.argv:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        strip = lambda s: re.sub(r'Generated: \S+', 'Generated:', s)
        if strip(cur) != strip(md):
            print('STALE: %s -- run scripts/build_annual_report_inventory.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok: %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(md)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return subprocess.call([sys.executable, os.path.join(ROOT, 'scripts', 'build_analysis_pdf.py'),
                            '--file', os.path.relpath(OUT, ROOT)], cwd=ROOT)


if __name__ == '__main__':
    sys.exit(main())
