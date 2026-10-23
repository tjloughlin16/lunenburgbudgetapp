#!/usr/bin/env python3
"""THE SCHOOL JOURNAL, AS A DATASET: what it holds, how it is redacted, what it cannot show.

    python3 scripts/build_school_journal.py           # write the markdown and the payload
    python3 scripts/build_school_journal.py --check   # fail if either is stale

    sources/analyses/school-journal.md       /analysis/school-journal (UNLISTED until TJ reviews)
    fy28/public/data/school-journal.json     its payload: stats, grain, conclusions, sources

WHAT THIS PAGE IS FOR. notes/plans/MUNIS-JOURNAL-REPORTS.md, Phase 0: "The journal data page:
grain, sources, the redaction rule, what it cannot show." Every journal report links here for
how to read a figure, so the reports do not each restate it. The pattern is
`build_annual_reports.py`: the downloads first (rule 7a, the thing first), then what the data
is, then what it cannot do.

EVERYTHING IS DERIVED, from the three published CSVs through scripts/journal.py, and the page
re-proves the one claim it leads with rather than quoting the extractor: that every account's
FY2026 lines add up to the figures the Town's report prints for it. That tie is recomputed
here from the two public files alone, so a reader can repeat it without the private PDF.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import conclusion, figure, emit  # noqa: E402
import journal as J  # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'analyses', 'school-journal.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-journal.json')
FILES = [('munis-school-journal.csv', 'every journal line', J.JOURNAL_CSV),
         ('munis-school-journal-accounts.csv', 'every account, with the FY2026 figures the '
          'report prints', J.ACCOUNTS_CSV),
         ('munis-school-journal-image-pages.csv', 'the lines of the three picture-only pages, '
          'read by eye and redacted by the same rule',
          os.path.join(J.DATA, 'munis-school-journal-image-pages.csv'))]
PROVENANCE = ('/docs/town-ledgers/account-details/'
              'PROVENANCE-fy2023-fy2026-p13-school-journal.md')
PRINTED = {'original_budget': 'original_approp', 'transfer': 'transfers_adjustments',
           'actual': 'ytd_actual', 'encumbrance': 'encumbrances'}
# Columns a reader needs first, and what each holds. The rest are in the CSV header.
COLUMNS = [
    ('fiscal_year, period', 'the MUNIS fiscal year and period; period 0 is the opening entry, '
     '13 the closing'),
    ('source', 'the MUNIS source code; see the table below'),
    ('posts_to', 'which column of the printed report the line adds to'),
    ('amount', 'dollars; a credit is negative'),
    ('fund, org, account, object', 'where it posts; `object` begins 5 for spending and 4 for '
     'revenue'),
    ('vendor, vendor_no', 'the payee, or `individual (redacted)` or empty where masked'),
    ('description, comment', 'the Town’s text, after our redaction'),
    ('masked', 'which fields on the line we masked, and why'),
    ('name_basis', 'the public record that shows a named person is an employee, or `paid as '
     'vendor`'),
    ('page, line', 'where the line is on the Town’s printed report'),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def mb(n):
    return '%.1f MB' % (n / 1e6) if n >= 1e6 else '%d KB' % round(n / 1024)


def facts():
    A, L = J.accounts(), J.lines()
    f = {'lines': len(L), 'accounts': len(A)}
    f['funds'] = len({a['fund'] for a in A.values()})
    f['years'] = sorted({r['fy'] for r in L})
    # THE TIE, from the public files alone: FY2026 lines against the printed figures.
    s = defaultdict(lambda: defaultdict(Decimal))
    for r in L:
        if r['fy'] == J.OPEN_FY:
            s[r['account']][r['posts_to']] += r['amt']
    off = [a for a, row in A.items()
           if any(s[a][k] != Decimal(row[col]) for k, col in PRINTED.items())]
    if off:
        raise SystemExit('build_school_journal: %d accounts no longer tie to their printed '
                         'FY2026 figures, e.g. %s' % (len(off), off[:3]))
    f['tied'] = len(A)
    f['by_source'] = Counter(r['source'] for r in L)
    f['by_year'] = {y: dict(lines=sum(1 for r in L if r['fy'] == y),
                            # spent: payments plus what was still owed (journal.py, WHAT
                            # "SPENT" MEANS) -- the figure /school-all-funds shows for the year
                            spent=sum(r['amt'] for r in L if r['fy'] == y and J.is_spent(r)
                                      and J.is_expense(A[r['account']])),
                            gf=sum(r['amt'] for r in L if r['fy'] == y and J.is_spent(r)
                                   and r['fund'] == '0100' and J.is_expense(A[r['account']])))
                    for y in f['years']}
    vnd = [r for r in L if r['ref_type'] == 'VND']
    f['vnd'] = len(vnd)
    f['vnd_masked'] = sum(1 for r in vnd if J.payee(r) is J.MASKED)
    f['payees'] = len({J.payee(r) for r in vnd if J.payee(r) is not J.MASKED})
    f['masked_lines'] = sum(1 for r in L if r['masked'])
    mf = Counter()
    for r in L:
        for x in filter(None, r['masked'].split(';')):
            mf[x.split(' (')[0]] += 1
    f['masked_fields'] = mf
    f['employees'] = sum(1 for r in L if r['name_basis'] and r['name_basis'] not in
                         ('paid as vendor', 'scholarship award'))
    pr = [r for r in L if J.KIND_OF.get(r['source']) == 'payroll']
    f['payroll_lines'] = len(pr)
    f['payroll_runs'] = {y: len({r['journal'] for r in pr if r['fy'] == y and r['source'] == 'PRJ'})
                         for y in f['years']}
    f['payroll_named'] = sum(1 for r in pr if r['vendor'] or r['vendor_no'])
    # The department the period-13 spreadsheets do not hold (org 13012, department 301).
    d301 = [a for a in A.values() if a['account'].split('-')[2] == '301']
    f['d301'] = dict(orgs=sorted({a['org'] + ' ' + a['org_name'] for a in d301}),
                     orig=sum(Decimal(a['original_approp']) for a in d301),
                     enc=sum(Decimal(a['encumbrances']) for a in d301),
                     avail=sum(Decimal(a['available_budget']) for a in d301))
    gf = [a for a in A.values() if a['fund'] == '0100']
    f['gf_enc'] = sum(Decimal(a['encumbrances']) for a in gf)
    f['gf_enc_300'] = f['gf_enc'] - f['d301']['enc']
    f['gf_orig_300'] = sum(Decimal(a['original_approp']) for a in gf
                           if a['account'].split('-')[2] == '300')
    f['image_lines'] = sum(1 for _ in csv.DictReader(open(FILES[2][2], encoding='utf-8')))
    f['files'] = [dict(name=n, what=w, url='/docs/data/' + n, bytes=os.path.getsize(p),
                       sha256=sha(p)) for n, w, p in FILES]
    return f


def payload(f):
    N = lambda v, u: figure(v, C.num(v), u)
    rows = [
        conclusion(
            id='every-account-ties-to-the-printed-report',
            claim='All %s school accounts add up, to the cent, to what the Town’s report prints.'
                  % C.num(f['tied']),
            so_what='A sum of these lines is the Town’s own figure, not our estimate of it.',
            figures={'n': N(f['tied'], 'accounts'),
                     'y': figure(J.OPEN_FY, C.fy(J.OPEN_FY), 'fiscal year')},
            figure='n', kind='measured',
            bearing='sizes',
            detail='For %s, every account’s lines, grouped by the column they post to, equal '
                   'the original budget, transfers, actual and encumbrances the report prints '
                   'for it. Recomputed here from the two public files alone.'
                   % C.fy(J.OPEN_FY),
            basis='munis-school-journal.csv against munis-school-journal-accounts.csv; the '
                  'extractor also ties every printed TOTAL line and the GRAND TOTAL.',
            not_shown='That the earlier years tie account by account: the report prints '
                      'figures for the last year only, and earlier years are tied to the '
                      'Town’s period-13 spreadsheets for the accounts both hold.'),
        conclusion(
            id='providers-named-families-masked',
            claim='%s of %s payee lines are masked; the other payees, %s of them, are named.'
                  % (C.num(f['vnd_masked']), C.num(f['vnd']), C.num(f['payees'])),
            so_what='Who the schools paid can be followed. Who received a service cannot.',
            figures={'m': N(f['vnd_masked'], 'lines'), 'v': N(f['vnd'], 'lines'),
                     'p': N(f['payees'], 'payees')}, figure='m', kind='measured',
            bearing='sizes',
            detail='A masked payee is a family or a child, hidden by the Town’s redaction or '
                   'by ours. Providers, vendors, and staff named in their role are kept.',
            basis='the `vendor` and `masked` columns of munis-school-journal.csv.',
            not_shown='Whether a masked line is one family or several: a masked payee loses '
                      'its vendor number, on purpose, so masked payees cannot be counted.'),
    ]
    yrs = f['years']
    return {
        'id': 'school-journal',
        'title': 'The school journal',
        'grain': 'One row per journal line: a single posting to one school account, in any '
                 'fund, with its date, source code, payee and description. A payroll line is '
                 'one account’s share of one pay run, not a person.',
        'stats': [
            {'value': C.num(f['lines']), 'label': 'journal lines, %s'
             % C.fyspan(yrs[0], yrs[-1])},
            {'value': C.num(f['accounts']), 'label': 'school accounts, in %s funds'
             % C.num(f['funds'])},
            {'value': C.num(f['payees']), 'label': 'payees named'},
            {'value': C.num(f['vnd_masked']), 'label': 'payee lines masked (families, children)'},
        ],
        'conclusions': emit('school-journal', rows),
        'files': f['files'],
        'sources': [
            {'what': 'How the journal reached us, and what the Town redacted',
             'where': PROVENANCE},
            {'what': 'The decision to publish our redacted reading, not the raw',
             'where': '/docs/data/redactions.csv'},
            {'what': 'The reading and the redaction rule, in full',
             'where': 'scripts/extract_munis_school_journal.py (its header)'},
            {'what': 'The definitions every journal report shares',
             'where': 'scripts/journal.py'},
        ],
        'not_established': [
            'The %s close: encumbrances were still open when the report was run, so every %s '
            'figure can still move.' % (C.fy(J.OPEN_FY), C.fy(J.OPEN_FY)),
            'What anything costs in full. A line is a posting to a school account; benefits '
            'and costs charged to other accounts are not in it.',
            'Who was paid on a pay run. Payroll lines carry no person.',
            'Who received a service. Families and children are masked and cannot be counted.',
            'Earlier years account by account against the report itself: it prints figures for '
            '%s only.' % C.fy(J.OPEN_FY),
        ],
    }


def render(f, pay):
    L = []
    w = L.append
    yrs = f['years']
    usd = C.usd
    w('# The school journal')
    w('')
    w('Every posting to every school account, %s, in every fund, with its payee and date.'
      % C.fyspan(yrs[0], yrs[-1]))
    w('')
    w('## The files')
    w('')
    w('| file | what it holds | size | sha256 |')
    w('|---|---|---:|---|')
    for x in f['files']:
        w('| [`%s`](%s) | %s | %s | `%s…` |' % (x['name'], x['url'], x['what'], mb(x['bytes']),
                                                x['sha256'][:16]))
    w('')
    w('Our redacted reading of the Town’s MUNIS report `glytdbud`, run with journal detail '
      'from %s period 0 to %s period 13 and delivered under a records request. The Town’s '
      'own PDF is held privately and not published; why, and what it is, is in the '
      '[provenance note](%s).' % (C.fy(yrs[0]), C.fy(yrs[-1]), PROVENANCE))
    w('')
    w('## What a line is')
    w('')
    w(pay['grain'])
    w('')
    w('| column | holds |')
    w('|---|---|')
    for k, v in COLUMNS:
        w('| `%s` | %s |' % (k, v))
    w('')
    w('### Source codes')
    w('')
    w('Which code adds to which column of the printed report is not assumed: it is the only '
      'assignment under which every account closes.')
    w('')
    w('| source | posts to | what produced it | lines |')
    w('|---|---|---|---:|')
    for s in sorted(J.COLUMN_OF, key=lambda s: (J.CLASSES.index(J.COLUMN_OF[s]), s)):
        w('| `%s` | %s | %s | %s |' % (s, J.COLUMN_OF[s].replace('_', ' '),
                                      J.KIND_OF.get(s, '—'), C.num(f['by_source'].get(s, 0))))
    w('')
    w('**Payroll lines are not people.** Every `PRJ` and `PRH` line is %s. %s pay runs '
      'posted in %s, %s in %s, %s in %s and %s in %s; %s of %s payroll lines name anyone.'
      % (J.PAYROLL_GRAIN, C.num(f['payroll_runs'][yrs[0]]), C.fy(yrs[0]),
         C.num(f['payroll_runs'][yrs[1]]), C.fy(yrs[1]), C.num(f['payroll_runs'][yrs[2]]),
         C.fy(yrs[2]), C.num(f['payroll_runs'][yrs[3]]), C.fy(yrs[3]),
         C.num(f['payroll_named']), C.num(f['payroll_lines'])))
    w('')
    w('### By year')
    w('')
    w('| fiscal year | lines | spending, every fund | of which general fund |')
    w('|---|---:|---:|---:|')
    for y in yrs:
        b = f['by_year'][y]
        w('| %s%s | %s | %s | %s |' % (C.fy(y), ' (not closed)' if y == J.OPEN_FY else '',
                                      C.num(b['lines']), usd(b['spent']), usd(b['gf'])))
    w('')
    w('Spending is payments plus what was still owed on expense accounts, net of every reversal '
      'and reclassification; only %s still owed anything when the report was run. It is the '
      'school ledger’s spending, not what the schools cost: see what it cannot show, below.'
      % C.fy(J.OPEN_FY))
    w('')
    w('## The redaction')
    w('')
    w('The rule is about one thing: never attaching a name to a disability or a service a '
      'child receives. So a child, or a parent acting for their child, is hidden wherever a '
      'line could tie them to one, and the people PAID to provide services are not.')
    w('')
    w('- **Providers and vendors are named**: name, service, amount, invoice and check number.')
    w('- **Recipients are masked**: a child, or a parent or family acting for their child. '
      'Their name, vendor number, invoice and check number go, and so does every trace of '
      'them the extractor finds in a description; it refuses to write if any survives.')
    w('- **Staff named in their role are kept** where a public record shows they are an '
      'employee: %s lines.' % C.num(f['employees']))
    w('- **A special education family is never named**, even on a transportation line, where '
      'other families are.')
    w('')
    w('%s lines carry at least one masked field. By field:' % C.num(f['masked_lines']))
    w('')
    w('| field masked | lines |')
    w('|---|---:|')
    for k, n in f['masked_fields'].most_common():
        w('| `%s` | %s |' % (k, C.num(n)))
    w('')
    w('The three pages the Town delivered as pictures are read by eye into `%s` (%s lines), '
      'through the same redaction.' % (FILES[2][0], C.num(f['image_lines'])))
    w('')
    w('**No report built on this journal may isolate a masked recipient.** A masked amount '
      'appears only inside an aggregate that also holds other payees.')
    w('')
    w('## How it differs from the period-13 spreadsheets')
    w('')
    d = f['d301']
    w('This run holds one general fund department the Town’s period-13 school spreadsheets do '
      'not: department 301, %s. It carried %s of the %s original budget, and %s of the %s '
      'still on order at the run; the spreadsheets’ department 300 holds the other %s. Its '
      'available balance at the run was %s.'
      % ('; '.join(d['orgs']), usd(d['orig']), C.fy(J.OPEN_FY), usd(d['enc']),
         usd(f['gf_enc']), usd(f['gf_enc_300']), usd(d['avail'])))
    w('')
    w('## What it cannot show')
    w('')
    for n in pay['not_established']:
        w('- %s' % n)
    w('')
    w('Limits that a better reading cannot close are registered in '
      '`sources/data/money-gaps.csv` and published at `/what-we-cannot-answer`.')
    w('')
    w('## Where it comes from')
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
        if not rc:
            print('school journal: page and payload current')
        return rc
    for path, text in ((OUT, doc), (PAYLOAD, js)):
        tmp = path + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='\n').write(text)
        os.replace(tmp, path)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
