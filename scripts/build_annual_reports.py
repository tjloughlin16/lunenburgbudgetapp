#!/usr/bin/env python3
"""THE ANNUAL TOWN REPORTS: every one of them, what is in it, and what we proved.

    python3 scripts/build_annual_reports.py           # write the markdown and the payload
    python3 scripts/build_annual_reports.py --check   # fail if either is stale

TJ, 28 September 2026: *"create a REPORT for annual reports, that lists all the reports
(and easily downloadable), whats in them (categorically). I want to see what we found in
the annual reports, categorically speaking"*

WHAT THIS PAGE IS FOR. Sixteen documents, 478 pages of financial tables, 25 datasets. A
resident who wants to check a figure has to be able to get to the document it came from,
and a reader who wants to know what the archive can answer has to see the CATEGORIES
rather than a list of files. So the page leads with the sixteen documents and their
download links -- rule 7a, the thing first -- and then says, per category, how much of it
is proved.

THE STATE OF A PAGE IS THE POINT, NOT THE COUNT OF PAGES. Every page here has been read;
none is unread. What separates them is whether anything CHECKED the figures:

    PROVEN     the rows tie to a total the page itself prints
    UNPROVEN   the rows exist and nothing has ever checked them
    REFUSED    an extractor reached the page and wrote nothing

That distinction is the whole reason this report exists. A reader looking at 478 read
pages would reasonably conclude the archive holds 478 pages of checked figures, and it
holds 162. The rest are real readings of real pages that no arithmetic has confirmed --
usable, quotable with the caveat, and not the same thing.

Everything here is DERIVED. The documents come from the archive manifest, the pages from
`annual-report-pages.csv`, the datasets from the same inventory `build_archive_guide.py`
publishes, so this page cannot drift from either.
"""
import argparse
import collections
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

DATA = os.path.join(ROOT, 'sources', 'data')
PAGES = os.path.join(DATA, 'annual-report-pages.csv')
MANIFEST = os.path.join(DATA, 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'annual-reports.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'annual-reports.json')

STATES = ('proven', 'unproven', 'refused')
# What a reader is actually looking for, in their words rather than ours. A subject slug
# is our filing; this is the question it answers.
SUBJECT_MEANS = {
    'appropriations': 'what Town Meeting voted to spend, article by article',
    'special-revenue': 'the funds that sit outside the budget \u2014 grants, gifts, revolving',
    'payroll': 'what the town paid its people, name by name',
    'debt': 'what the town owes and when it falls due',
    'trust-and-stabilization': 'the reserves, and how much is in each',
    'receivables': 'what is owed TO the town, account by account',
    'tax-collection': 'what was committed, collected and abated',
    'regional-school': 'the assessment from the regional school district',
    'balance-sheet': 'what the town held and owed at year end',
    'valuation': 'what the town is worth, by class of property',
    'treasurers-cash': 'the cash the Treasurer held',
    'capital': 'the capital projects and what they cost',
    'enrollment': 'how many children are in the schools',
    'elections': 'how the town voted',
    'cultural-council': 'the grants the cultural council made',
    'unknown': 'a financial table whose heading we could not classify',
}


def pages():
    with open(PAGES, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def documents():
    """The sixteen reports, from the manifest, with the address a reader can fetch."""
    out = []
    with open(MANIFEST, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            k = r['key']
            if not k.startswith('town-annual-reports/docs/') or not k.endswith('.pdf'):
                continue
            name = os.path.basename(k)
            fy = ''.join(c for c in name.split('fy-')[-1][:4] if c.isdigit()) \
                if 'fy-' in name else ''
            out.append({'fy': fy, 'file': name, 'key': k,
                        'bytes': int(r['bytes']), 'sha256': r['sha256'],
                        'url': '/docs/' + k,
                        'addendum': 'addendum' in name})
    out.sort(key=lambda d: (d['fy'], d['addendum']))
    return out


def by_subject(rows):
    out = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        out[r['subject']][r['state']] += 1
    return out


def by_fy(rows):
    out = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        out[r['fy']][r['state']] += 1
    return out


def datasets():
    """The same inventory the archive guide publishes, so the two cannot disagree.

    BOTH FAMILIES, because they are read differently and a reader has to know which.
    A dedicated extractor knows what its table means and can check it against a total the
    page prints. The generic one does not: its `v1`...`v8` are ORDINALS -- the first,
    second, third column of THAT page that held figures -- and the column ruler is rebuilt
    per page, so summing `v1` across a run adds one page's APPROPRIATED to another's TOTAL
    EXPENDED. `column_meaning` is what names them where the table states an identity that
    fixes them, and says `not established` where it does not.
    """
    import glob
    import build_archive_guide as G
    out = []

    def add(name, what, proof, built_by):
        rws = G.rows_of(name)
        if not rws:
            return
        st = collections.Counter(r.get('status', '') for r in rws)
        graded = st['checked'] + st['check failed'] + st['no check']
        out.append({'name': name, 'rows': len(rws), 'years': G.years(rws),
                    'what': what, 'checked': st['checked'],
                    'failed': st['check failed'], 'nocheck': st['no check'],
                    'graded': graded, 'proof': proof, 'built_by': built_by})

    for name, what, proof in getattr(G, 'HAND', []):
        add(name, what, proof, 'dedicated')
    for p in sorted(glob.glob(os.path.join(DATA, 'report-*.csv'))):
        name = os.path.basename(p)[:-4]
        if name == 'report-anomalies':
            continue
        add(name, '', '', 'generic')
    out.sort(key=lambda d: -d['rows'])
    return out


def mb(n):
    return '%.1f MB' % (n / 1048576.0)


def facts():
    rows = pages()
    docs = documents()
    ds = datasets()
    st = collections.Counter(r['state'] for r in rows)
    subj = by_subject(rows)
    fys = sorted({r['fy'] for r in rows})
    ranked = sorted(subj.items(), key=lambda kv: -sum(kv[1].values()))
    worst = max(subj.items(), key=lambda kv: kv[1]['unproven'])
    return {'rows': rows, 'docs': docs, 'datasets': ds, 'state': st, 'subject': subj,
            'ranked': ranked, 'worst': worst, 'fys': fys,
            'total': len(rows), 'dataset_rows': sum(d['rows'] for d in ds)}


def payload(f):
    import conclusions as C
    from conclusions import conclusion, emit, figure

    st, total = f['state'], f['total']
    proven, unproven, refused = st['proven'], st['unproven'], st['refused']
    docs, ds = f['docs'], f['datasets']
    wsub, wc = f['worst']
    dedicated = [d for d in ds if d['built_by'] == 'dedicated']
    generic = [d for d in ds if d['built_by'] == 'generic']

    rws = [
        conclusion(
            id='every-financial-page-has-been-read',
            claim='All %s pages holding a financial table have been read.' % C.num(total),
            so_what='None is unread, so the work left is checking rather than reading.',
            figures={'pages': figure(total, C.num(total),
                                     'pages holding a financial table')},
            figure='pages', kind='measured', bearing='sizes',
            detail='Sixteen documents, opened page by page. A page counted here is one '
                   'that holds a financial table, not every page of the book.',
            basis='`annual-report-pages.csv`, which is generated from what the extractors '
                  'actually wrote and refuses to publish a count off a stale database.',
            not_shown='Whether a page holds a table we have not recognised as financial. '
                      'The classifier reads headings, and the pages whose heading did not '
                      'classify are filed as `unknown` rather than dropped.',
        ),
        conclusion(
            id='a-third-of-the-pages-are-checked-against-the-page-itself',
            claim='%s of %s pages tie to a total the page itself prints.'
                  % (C.num(proven), C.num(total)),
            so_what='The other %s carry real figures that no arithmetic has confirmed.'
                    % C.num(unproven + refused),
            figures={'proven': figure(proven, C.num(proven), 'pages tied to a printed total'),
                     'all': figure(total, C.num(total), 'pages holding a financial table'),
                     'rest': figure(unproven + refused, C.num(unproven + refused),
                                    'pages with no such check')},
            figure='proven', kind='measured', bearing='sizes',
            detail='A page is PROVEN only where the table states an identity about itself '
                   '-- parts summing to a printed total -- and the extract closes it. '
                   'Most tables here print no total, so there is nothing to close.',
            basis='the `state` column of `annual-report-pages.csv`, set from the proof '
                  'each extractor recorded rather than from whether it produced rows.',
            not_shown='That an UNPROVEN figure is wrong. It means nothing has checked it, '
                      'which is a different claim and the reason the column exists.',
        ),
        conclusion(
            id='the-largest-unchecked-category-is-what-town-meeting-voted',
            claim='%s is the least checked: %s of its %s pages have no check at all.'
                  % (wsub.replace('-', ' ').title(), C.num(wc['unproven']),
                     C.num(sum(wc.values()))),
            so_what='It is also the category a resident is most likely to quote.',
            figures={'un': figure(wc['unproven'], C.num(wc['unproven']),
                                  'pages with no check'),
                     'tot': figure(sum(wc.values()), C.num(sum(wc.values())),
                                   'pages in this category'),
                     'ok': figure(wc['proven'], C.num(wc['proven']),
                                  'pages tied to a printed total')},
            figure='un', kind='measured', bearing='lever',
            detail='These pages print what Town Meeting voted, article by article. %s of '
                   'them do tie to a printed total; the rest are read and unconfirmed.'
                   % C.num(wc['proven']),
            basis='`annual-report-pages.csv` grouped by subject and state.',
            not_shown='Which of those pages COULD be checked. A page printing no total '
                      'can never reach PROVEN however good the extractor gets.',
        ),
        conclusion(
            id='two-extractors-read-these-tables-and-they-are-not-equal',
            claim='%s of the %s datasets are read by a generic extractor that cannot name '
                  'its columns.' % (C.num(len(generic)), C.num(len(ds))),
            so_what='Read `column_meaning` before quoting a value from one of those.',
            figures={'gen': figure(len(generic), C.num(len(generic)),
                                   'datasets read generically'),
                     'ded': figure(len(dedicated), C.num(len(dedicated)),
                                   'datasets with a dedicated extractor'),
                     'all': figure(len(ds), C.num(len(ds)),
                                   'datasets from these reports')},
            figure='gen', kind='measured', bearing='sizes',
            detail='The generic extractor records a column as `v1`, `v2`, `v3` -- an '
                   'ORDINAL, the first column of THAT page that held figures. The ruler '
                   'is rebuilt per page, so the same name means different columns on '
                   'different pages.',
            basis='the dataset inventory in `scripts/build_archive_guide.py`, read here '
                  'rather than restated, so the two cannot disagree.',
            not_shown='Which printed column a given `v1` is on any particular page, '
                      'except where `column_meaning` names it from an identity the table '
                      'states about itself.',
            allow=('v1', 'v2', 'v3'),
        ),
    ]

    return {
        'id': 'annual-reports',
        'title': 'The annual town reports',
        'grain': 'One row per page of an annual town report that holds a financial table, '
                 'and the datasets read out of those pages. A page is counted once per '
                 'report; a figure is counted once per row.',
        'stats': [
            {'value': C.num(len(docs)), 'label': 'annual town reports, %s–%s'
             % (C.fy(int(f['fys'][0])), C.fy(int(f['fys'][-1])))},
            {'value': C.num(total), 'label': 'pages holding a financial table'},
            {'value': '%s of %s' % (C.num(proven), C.num(total)),
             'label': 'pages tied to a total the page prints'},
            {'value': C.num(f['dataset_rows']), 'label': 'rows read out of them'},
        ],
        'conclusions': emit('annual-reports', rws),
        'documents': [{'fy': d['fy'], 'file': d['file'], 'url': d['url'],
                       'size': mb(d['bytes']), 'sha256': d['sha256'],
                       'addendum': d['addendum']} for d in docs],
        'categories': [
            {'subject': s, 'means': SUBJECT_MEANS.get(s, ''),
             'pages': sum(c.values()), 'proven': c['proven'],
             'unproven': c['unproven'], 'refused': c['refused']}
            for s, c in f['ranked']],
        'datasets': [{'name': d['name'], 'rows': d['rows'], 'years': d['years'],
                      'built_by': d['built_by'], 'checked': d['checked'],
                      'failed': d['failed'], 'nocheck': d['nocheck']} for d in ds],
        'sources': [
            {'what': 'The sixteen reports themselves',
             'where': '/docs/town-annual-reports/docs/, each with its sha256 in '
                      '/data/archive-manifest.csv'},
            {'what': 'What is on each page and what proved it',
             'where': '/data/annual-report-pages.csv'},
            {'what': 'What a column means before you quote it',
             'where': 'sources/data/PROVENANCE-report-tables.md and `column_meaning`'},
        ],
        'not_established': [
            'That an UNPROVEN figure is wrong. Nothing has checked it.',
            'What a generic `v1` column is on any page where `column_meaning` says '
            '`not established`.',
            'Whether a page we filed as `unknown` holds a table worth reading.',
        ],
    }


def render(f, pay):
    """The document. Rule 7a: the sixteen reports first, the method underneath."""
    L = []
    w = L.append
    st, total = f['state'], f['total']

    w('# The annual town reports')
    w('')
    w('Sixteen documents, %s pages of financial tables, %s rows read out of them.'
      % (f'{total:,}', f'{f["dataset_rows"]:,}'))
    w('')
    w('## The short version')
    w('')
    w('- Every financial page in every report has been read. **None is unread.**')
    w('- **%s of %s** tie to a total the page itself prints. The rest are real readings '
      'that no arithmetic has confirmed.' % (f'{st["proven"]:,}', f'{total:,}'))
    w('- **%s pages** an extractor reached and wrote nothing from. Each says why.'
      % f'{st["refused"]:,}')
    w('- What is left is **code, not reading**.')
    w('')

    w('## The sixteen reports')
    w('')
    w('Every one is downloadable, and every one carries the sha256 of the bytes we hold, '
      'so a figure can be traced to the page it came from and the page to the file.')
    w('')
    w('| fiscal year | document | size | download | sha256 |')
    w('|---|---|---:|---|---|')
    for d in f['docs']:
        label = 'FY%s%s' % (d['fy'], ' addendum' if d['addendum'] else '')
        w('| %s | `%s` | %s | [download](%s) | `%s…` |'
          % (label, d['file'], mb(d['bytes']), d['url'], d['sha256'][:16]))
    w('')

    w('## What is in them, by category')
    w('')
    w('`proven` means the rows tie to a total the page itself prints. `unproven` means '
      'the rows exist and nothing has checked them — **not** that they are wrong. '
      '`refused` means an extractor reached the page and wrote nothing.')
    w('')
    w('| category | what it answers | pages | proven | unproven | refused |')
    w('|---|---|---:|---:|---:|---:|')
    for s, c in f['ranked']:
        w('| %s | %s | %d | %d | %d | %d |'
          % (s.replace('-', ' '), SUBJECT_MEANS.get(s, ''), sum(c.values()),
             c['proven'], c['unproven'], c['refused']))
    w('| **total** |  | **%d** | **%d** | **%d** | **%d** |'
      % (total, st['proven'], st['unproven'], st['refused']))
    w('')

    w('## By report')
    w('')
    w('| fiscal year | pages | proven | unproven | refused |')
    w('|---|---:|---:|---:|---:|')
    byf = by_fy(f['rows'])
    for fy in sorted(byf):
        c = byf[fy]
        w('| FY%s | %d | %d | %d | %d |'
          % (fy, sum(c.values()), c['proven'], c['unproven'], c['refused']))
    w('')

    w('## The datasets read out of them')
    w('')
    w('A **dedicated** extractor knows what its table means and can check it against a '
      'total the page prints. The **generic** one cannot: its `v1`…`v8` are ORDINALS — '
      'the first, second, third column of *that page* that held figures — and the ruler '
      'is rebuilt per page. Read `column_meaning` before quoting one.')
    w('')
    w('| dataset | rows | years | built by | checked | check failed | no check |')
    w('|---|---:|---|---|---:|---:|---:|')
    for d in f['datasets']:
        grade = ('%d | %d | %d' % (d['checked'], d['failed'], d['nocheck'])) \
            if d['graded'] else ' — | — | — '
        w('| `%s.csv` | %s | %s | %s | %s |'
          % (d['name'], f'{d["rows"]:,}', d['years'], d['built_by'], grade))
    w('')

    w('## What this does not establish')
    w('')
    for n in pay['not_established']:
        w('- %s' % n)
    w('')
    w('Limits that cannot be closed by better code are registered in '
      '`sources/data/money-gaps.csv` and published at `/what-we-cannot-answer`.')
    w('')

    w('## Where these figures come from')
    w('')
    w('| what | where |')
    w('|---|---|')
    for s in pay['sources']:
        w('| %s | %s |' % (s['what'], s['where']))
    w('')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    f = facts()
    pay = payload(f)
    doc = render(f, pay)
    js = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        rc = 0
        for path, want in ((OUT, doc), (PAYLOAD, js)):
            cur = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if cur != want:
                print('STALE %s' % os.path.relpath(path, ROOT))
                rc = 1
        return rc
    os.makedirs(os.path.dirname(PAYLOAD), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(doc)
    open(PAYLOAD, 'w', encoding='utf-8').write(js)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    print('  %d reports, %d pages (%d proven / %d unproven / %d refused), %d datasets, '
          '%s rows' % (len(f['docs']), f['total'], f['state']['proven'],
                       f['state']['unproven'], f['state']['refused'],
                       len(f['datasets']), f'{f["dataset_rows"]:,}'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
