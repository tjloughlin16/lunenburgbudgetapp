#!/usr/bin/env python3
"""THE FY2026 SCHOOL BUDGET AGAINST MUNIS, line by line: did the budget the School Committee
approved on 12 March 2025 land in the Town's books on the same code at the same amount?

    python3.11 scripts/build_budget_vs_munis.py           # write fy28/public/data/topics/fy2026-budget-vs-munis.json
    python3.11 scripts/build_budget_vs_munis.py --check   # fail if it would change

    fy2026-budget-vs-munis   /fy2026-closeout/fy2026-budget-vs-munis   Budget against MUNIS

TJ, 25 November 2026, on the code reconciliation workbook: "I would like to see an actual report on
this and associate it to the FY closeout hub ... what percentage from the approved budget landed in
munis exactly ... how many are off as percentages call out the line items that are off by how much".
And the same day: "why are we using a workbook built in FY27 ... we need to use the OFFICIAL FY26
budget docs". Relayed 25 November: "definitely regenerate it to be factually true".

WHAT IT RESTS ON. The budget side is the OFFICIAL March budget, sources/data/fy26-approved-budget-
lines.csv (scripts/extract_fy26_approved_budget.py: every line of FINAL FY26 Town Manager's Target
Budget Approved 3-12-25, tied to the sums the page prints). The FY2027 workbook is not read: it
carries FY2026 at the MUNIS figures, so it cannot be the budget MUNIS is checked against. The MUNIS
side is the Town Accountant's year-to-date report for FY2026 period 12, ORIGINAL APPROP,
departments 300 and 301 (check_function_crosswalk.school_ledger).

HOW A LINE IS MATCHED: extract_fy26_approved_budget.against_munis(), the one rule the finding
notes/findings/FY26-BUDGET-THREE-WAYS.md also uses -- same code and amount; else the amount under
another code; else several March lines summing to one account; else the amount changed. Amount is
not a key (rule 13): a match shows a figure of that size on both sides, never that the two are the
same line. Which document codes a line correctly is not settled here.

WHAT A CODE IS CALLED. MUNIS prints no name for a function code. A code's name here is the March
budget's own heading for it; where the budget has none, DESE's, labelled as DESE's.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import build_fy2026_closeout_topics as CT  # noqa: E402
import check_function_crosswalk as XW  # noqa: E402
import extract_fy26_approved_budget as X  # noqa: E402

ID = 'fy2026-budget-vs-munis'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
APPROPRIATED = 26287474.00   # checked below against the MUNIS original appropriation, not used alone
MARCH_DATE = '12 March 2025'


def fail(msg):
    raise SystemExit('build_budget_vs_munis: ' + msg)


def m(v):
    return X.money(v)


def data():
    led = XW.school_ledger()
    off = X.march_lines()
    total_led = round(sum(m(a['original']) for a in led), 2)
    if abs(total_led - APPROPRIATED) > 0.005:
        fail('the MUNIS original appropriation is no longer %s' % C.usd(APPROPRIATED))
    printed = X.EXPECTED_TOTAL            # the March TOTAL BUDGET, as every copy prints it
    gap = round(total_led - printed, 2)
    M = X.against_munis(off, led)
    lines = [x for x in off if abs(x['fy26'] or 0) >= 0.5]

    # Every MUNIS dollar is in exactly one of these, or the page's chart would not add up.
    part = dict(landed=sum(m(a['original']) for _, a in M['landed']),
                moved=sum(m(a['original']) for _, a in M['moved']),
                joined=sum(m(a['original']) for _, a in M['joined']),
                spare=sum(m(a['original']) for a in M['spare']))
    part = {k: round(v, 2) for k, v in part.items()}
    if abs(sum(part.values()) - total_led) > 0.005:
        fail('the four parts of MUNIS sum to %s, not %s' % (sum(part.values()), total_led))

    # Code by code, what changed: March lines no account holds against accounts no line claims.
    codes = sorted({x['code'] for x in M['unlanded']} | {a['function'] for a in M['spare']})
    changes = []
    for c in codes:
        ms = round(sum(x['fy26'] for x in M['unlanded'] if x['code'] == c), 2)
        mu = round(sum(m(a['original']) for a in M['spare'] if a['function'] == c), 2)
        secs = {x['section'] for x in M['unlanded'] if x['code'] == c} | {
            section_of(a) for a in M['spare'] if a['function'] == c}
        changes.append(dict(code=c, march=ms, munis=mu, diff=round(mu - ms, 2), sections=secs))
    net = round(sum(r['diff'] for r in changes), 2)

    sw = [(x, a) for x, a in M['moved'] if 'social worker' in x['line'].lower()]
    if not (len(sw) == 4 and {x['code'] for x, _ in sw} == {'2900'} and {a['function'] for _, a in sw} == {'2710'}):
        fail('the page says four social worker lines sit under 2900 in March and 2710 in MUNIS')
    naked = [a for a in led if abs(m(a['original'])) < 0.5 and abs(m(a['transfers'])) < 0.5
             and abs(m(a['expended'])) >= 0.5]
    naked.sort(key=lambda a: -m(a['expended']))
    return dict(led=led, off=off, lines=lines, M=M, part=part, total_led=total_led, printed=printed,
                gap=gap, changes=changes, net=net, sw=sw, naked=naked)


def section_of(a):
    """Salaries or expenses, from the MUNIS object code: the account string's last segment, whose
    51xxxx objects are salaries (511001 teachers, 511024 social workers) in this ledger."""
    return 'salaries' if a['account'].rsplit('-', 1)[-1].startswith('51') else 'expenses'


def sources():
    s = CT.sources()
    man = {r.split(',', 1)[0] for r in open(os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv'),
                                             encoding='utf-8')}
    docs = {
        'mar': ('district-budget/docs/final-fy26-town-manager-39-s-target-budget-approved-3-12-25.pdf',
                'Lunenburg Public Schools'),
        'sc0402': ('meetings/school-committee/2025-04-02-minutes-rr2026-11-23.pdf',
                   'Lunenburg School Committee'),
        'fc0127': ('meetings/finance-committee/2026-01-27-minutes-7619.pdf', 'Lunenburg Finance Committee'),
    }
    out = [dict(s['p12'], key='p12')]
    for k, (key, pub) in docs.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out.append(dict(key=k, label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key))
    if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', 'fy26-approved-budget-lines.csv')):
        fail('/docs/data/fy26-approved-budget-lines.csv is not published')
    out += [dict(key='d-mar', label='Lunenburg Budget Project — fy26-approved-budget-lines.csv (the approved '
                                    'school budget, line by line)', href='/docs/data/fy26-approved-budget-lines.csv'),
            dict(s['d-ledger'], key='d-ledger'),
            dict(key='dese', label='DESE — Chart of Accounts, Criteria for Financial Reporting, '
                                   'July 2022 (dese-chart-of-accounts-2022-07.docx)',
                 href='/docs/state-dese/dese-chart-of-accounts-2022-07.docx')]
    return out


def code_names(off):
    """{(section, code): [the approved budget's headings for that code]}, one heading per school
    collapsed to one ('P.S. Repairs', 'H.S. Repairs' are one name for the code)."""
    out = {}
    for x in off:
        if not x['code']:
            continue
        nm = re.sub(r'^(?:[PEMH]\.\s?S\.|(?:Primary|Elementary|Middle|High) School)\s*', '', x['group'])
        nm = re.sub(r'\s*-\s*', ' - ', nm).strip()
        out.setdefault((x['section'], x['code']), [])
        if nm not in out[(x['section'], x['code'])]:
            out[(x['section'], x['code'])].append(nm)
    return out


def page(f):
    U = lambda v: C.usd(v)  # noqa: E731
    UF = lambda v: figure(v, C.usd(v))  # noqa: E731
    P = lambda v, dp=0: figure(v, C.pct(v, dp))  # noqa: E731
    N = lambda v, unit=None: figure(v, C.num(v), unit)  # noqa: E731
    fact, con = LD.fact, TP.conclusion
    M, part = f['M'], f['part']
    dese = XW.dese_function_names()
    names = code_names(f['off'])

    def named(c, sections):
        if not c or c == 'none':
            return 'no code'
        nm = []
        for s in sorted(sections):
            for n_ in names.get((s, c), []):
                if n_ not in nm:
                    nm.append(n_)
        if nm:
            return '%s %s' % (c, ' / '.join(nm))
        return '%s %s (DESE’s name)' % (c, dese[c]) if c in dese else '%s (unnamed)' % c

    n, nl = len(f['lines']), len(M['landed'])
    nmv, nj = len(M['moved']), len(M['joined'])
    pu = 100.0 * part['landed'] / f['total_led']
    sw_usd = round(sum(x['fy26'] for x, _ in f['sw']), 2)
    nk_usd = round(sum(m(a['expended']) for a in f['naked']), 2)
    nk_top = f['naked'][0]
    if 'KIND' not in nk_top['name']:
        fail('the last conclusion says kindergarten aides are the largest unbudgeted spending')
    nch = len(f['changes'])
    gap = f['gap']
    if abs(gap - 500000) > 0.005:
        fail('the page is built around MUNIS being $500,000 above the approved budget; it is %s' % gap)
    G = UF(gap)

    facts = [
        fact('total', UF(f['total_led']), 'appropriated, MUNIS original budget', 'published'),
        fact('march', UF(f['printed']), 'TOTAL BUDGET, approved %s' % MARCH_DATE, 'published',
             allow=(MARCH_DATE,)),
        fact('gap', G, 'MUNIS above the approved budget', 'published'),
        fact('landed', UF(part['landed']), 'MUNIS on a budget line’s code and amount', 'published'),
        fact('spare', UF(part['spare']), 'MUNIS in accounts whose amount differs', 'published'),
        fact('nch', N(nch, 'codes'), 'codes where an amount changed', 'published'),
        fact('net', UF(f['net']), 'net of those changes, MUNIS minus approved', 'published'),
        fact('n', N(n, 'lines'), 'approved-budget lines with an amount', 'published'),
        fact('mv', N(nmv, 'lines'), 'approved-budget lines under a different code in MUNIS', 'published'),
        fact('sw', UF(sw_usd), 'four social workers: 2900 in the budget, 2710 in MUNIS', 'published',
             allow=('2900', '2710')),
        fact('nk', N(len(f['naked']), 'accounts'), 'MUNIS accounts with no budget that spent',
             'published'),
        fact('nku', UF(nk_usd), 'what they spent by June', 'published'),
    ]
    conclusions = [
        con('MUNIS opened FY2026 with %s more than the approved school budget.' % U(gap),
            ['total', 'march', 'gap'], {'g': G}, allow=('FY2026',),
            so='%s of MUNIS sits on a budget line’s code and amount; %s in accounts whose amount differs.'
               % (C.pct(pu, 0), U(part['spare'])),
            so_figures={'p': P(pu), 's': UF(part['spare'])}),
        con('In %s codes an amount changed between the approved budget and MUNIS, by %s net.' % (C.num(nch), U(f['net'])),
            ['nch', 'net', 'spare', 'landed'], {'c': N(nch), 'n': UF(f['net'])},
            so='The changes do not say which of them is the %s and which is money moved between lines.'
               % U(gap), so_figures={'g': G}),
        con('%s of %s approved-budget lines sit under another code in MUNIS, at the same amount.'
            % (C.num(nmv), C.num(n)), ['n', 'mv', 'sw'], {'a': N(nmv), 'b': N(n)},
            so='The four social workers are %s of it: code 2900 in the approved budget, 2710 in MUNIS.' % U(sw_usd),
            so_figures={'s': UF(sw_usd)}, so_allow=('2900', '2710')),
        con('%s MUNIS accounts had no budget and no transfer, and spent %s by June.'
            % (C.num(len(f['naked'])), U(nk_usd)), ['nk', 'nku'],
            {'n': N(len(f['naked'])), 'u': UF(nk_usd)},
            so='Kindergarten aides are %s of it; the approved budget does not budget them.'
               % U(m(nk_top['expended'])), so_figures={'k': UF(m(nk_top['expended']))}),
    ]

    chart = TP.parts(
        'Where MUNIS’s school budget came from',
        [('On a budget line, same code', part['landed']),
         ('A budget amount, another code', part['moved']),
         ('Several budget lines, one account', part['joined']),
         ('Not an amount the budget printed', part['spare'])], '$',
        note='MUNIS’s FY2026 original appropriation, period 12, by whether the budget approved on %s '
             'prints the amount.' % MARCH_DATE,
        note_figures={'p': N(12)}, note_allow=(MARCH_DATE, 'FY2026'))

    # ---- where the amounts changed ----------------------------------------------------------
    change_table = dict(
        caption='Where the amounts changed, code by code',
        views=[dict(
            key='codes', label='Budget lines no account holds, against accounts no line claims',
            total_col=2, kinds=['ledger'] * 3,
            columns=['Approved budget', 'MUNIS', 'MUNIS minus approved'],
            rows=[dict(label=named(r['code'], r['sections']),
                       cells=[U(r['march']), U(r['munis']), U(r['diff'])])
                  for r in sorted(f['changes'], key=lambda r: -abs(r['diff']))]
            + [dict(label='All', cells=[U(sum(r['march'] for r in f['changes'])),
                                        U(sum(r['munis'] for r in f['changes'])), U(f['net'])])],
            note='In each code, the budget lines whose amount no MUNIS account holds, and the MUNIS '
                 'accounts whose amount no budget line prints. Code names are the approved budget’s '
                 'headings; MUNIS prints none.')])
    lines_table = dict(
        caption='The lines and accounts that changed',
        views=[dict(key='march', label='Budget lines not found in MUNIS', total_col=1,
                    kinds=['ledger'] * 2, columns=['Code', 'Amount'],
                    rows=[dict(label=x['line'], cells=[named(x['code'], {x['section']}), U(x['fy26'])])
                          for x in sorted(M['unlanded'], key=lambda x: (x['code'], -x['fy26']))]
                    + [dict(label='All', cells=['', U(sum(x['fy26'] for x in M['unlanded']))])],
                    note='As the approved budget prints them.'),
               dict(key='munis', label='MUNIS accounts not in the budget', total_col=1,
                    kinds=['ledger'] * 2, columns=['Code', 'Amount'],
                    rows=[dict(label='%s (%s)' % (a['name'].strip(), a['account']),
                               cells=[named(a['function'], {section_of(a)}),
                                      U(m(a['original']))])
                          for a in sorted(M['spare'], key=lambda a: (a['function'], -m(a['original'])))]
                    + [dict(label='All', cells=['', U(sum(m(a['original']) for a in M['spare']))])],
                    note='Names are as MUNIS prints them.')])

    # ---- lines under another code, or several lines in one account ---------------------------
    off_table = dict(
        caption='The budget lines that land under another code or in one account',
        views=[dict(
            key='off', label='Budget line against MUNIS', total_col=2,
            kinds=['ledger'] * 3,
            columns=['District budget code', 'MUNIS code and account', 'Amount'],
            rows=[dict(label=x['line'], cells=[named(x['code'], {x['section']}),
                                               '%s, account %s' % (named(a['function'], {x['section']}),
                                                                   a['name'].strip()),
                                               U(x['fy26'])])
                  for x, a in sorted(M['moved'], key=lambda p: -p[0]['fy26'])]
            + [dict(label=' + '.join('%s %s' % (x['line'], U(x['fy26'])) for x in hit),
                    cells=[named(a['function'], {hit[0]['section']}),
                           'same code, one account: %s' % a['name'].strip(), U(m(a['original']))])
               for hit, a in M['joined']]
            + [dict(label='All', cells=['', '', U(part['moved'] + part['joined'])])],
            note='A code’s name is the approved budget’s heading for it: MUNIS prints no names, only '
                 'the code inside the account string. Accounts are named as MUNIS prints them. '
                 '%s are not codes in DESE’s chart of accounts. A line '
                 'matched by amount is not proven to be the same line: amount is not a key, and '
                 'equal amounts pair arbitrarily.' % ', '.join(sorted(
                     {c for x, a in M['moved'] for c in (x['code'], a['function'])
                      if c and c not in dese})))])
    naked_table = dict(
        caption='MUNIS accounts with no budget and no transfer that spent',
        views=[dict(
            key='naked', label='MUNIS, period 12', total_col=2, kinds=['ledger'] * 3,
            columns=['Code', 'Account', 'Spent by June'],
            rows=[dict(label=a['name'].strip(), cells=[a['function'], a['account'],
                                                       U(m(a['expended']))])
                  for a in f['naked']]
            + [dict(label='All', cells=['', '', U(nk_usd)])],
            note='Names are as MUNIS prints them. Period 12 is June, before the close.')])

    # ---- the explanations -------------------------------------------------------------------
    where = TB.explain('Where the difference went', [
        ('The School Committee minutes of 2 April 2025 list an article to add %s to the FY2026 '
         'school budget, and the Finance Committee minutes of 27 January 2026 speak of “the '
         'additional %s for schools”. Neither says which lines it went to.' % (U(gap), U(gap)),
         {'g': G}, ('2 April 2025', 'FY2026', '27 January 2026')),
        ('That the difference above is that article is a reading: the amounts match, and nothing '
         'here tests it. The line-by-line spread is not in any document held. The line-item '
         'budget as voted at Town Meeting, or the district’s own allocation, would settle it.',
         None, ()),
    ], place='body', tone='plain')
    joined_ps = []
    for hit, a in M['joined']:
        figs = {'s': figure(m(a['original']), U(m(a['original'])))}
        for i, x in enumerate(hit):
            figs['l%d' % i] = figure(x['fy26'], U(x['fy26']))
        joined_ps.append((
            '%s: the approved budget prints %s; MUNIS holds one account, %s, at %s.' % (
                named(a['function'], {hit[0]['section']}),
                ' and '.join('%s at %s' % (x['line'], U(x['fy26'])) for x in hit),
                a['name'].strip(), U(m(a['original']))),
            figs, tuple([a['function']] + [x['line'] for x in hit]
                        + [n_ for s in (hit[0]['section'],) for n_ in names.get((s, a['function']), [])])))
    define = TB.explain('How to read the lines that do not land', [
        ('**Under another code.** The same amount is in both documents, filed under a different '
         'function code. The four social workers are filed under %s in the approved budget and %s in MUNIS.'
         % ('2900', '2710'), None, ('2900', '2710')),
        ('**Changed.** In the same code, a budget line whose amount no MUNIS account holds, and an '
         'account whose amount no budget line prints: the amount changed between the approved budget and the '
         'start of the year.', None, ()),
        ('**Several lines, one account.** The code agrees, but the approved budget prints two lines where MUNIS '
         'holds one account at their sum:', None, ()),
    ] + joined_ps, place='body', tone='define')
    which = TB.explain('Which coding is right', [
        'Neither document says, and this page does not choose. DESE’s chart of accounts names the '
        'codes a district reports to the state; it is silent on how the Town’s ledger or the '
        'district’s budget code their own lines. It lists social workers under '
        'psychological services, and adjustment counselors under guidance.',
    ], place='body', tone='plain')
    copies = TB.explain('Which budget document', [
        ('The budget approved on %s survives in five copies. All print the same total, and they '
         'print three different salary pages. This page reads the copy whose lines add up to the '
         'sums it prints itself.' % MARCH_DATE, None, (MARCH_DATE,)),
    ], place='body', tone='plain')

    cite = TP.cite
    flow = [
        'finding',
        cite(('chart', 0), 'mar', 'p12', 'd-mar', 'd-ledger'), ('conclusion', 0),
        cite(where, 'sc0402', 'fc0127'),
        cite(('table', 0), 'mar', 'p12', 'd-mar', 'd-ledger'), ('conclusion', 1),
        cite(('table', 1), 'mar', 'p12', 'd-mar', 'd-ledger'),
        cite(define, 'mar', 'p12'),
        cite(('table', 2), 'mar', 'p12', 'd-mar', 'd-ledger'), ('conclusion', 2),
        cite(which, 'dese'),
        cite(('table', 3), 'p12', 'd-ledger'), ('conclusion', 3),
        cite(copies, 'mar', 'd-mar'),
        'sources',
    ]
    return TP.page(
        ID,
        'MUNIS opened FY2026 with %s more for the schools than the approved school budget.' % U(gap),
        facts, conclusions, chart=chart, table=change_table,
        tables=[lines_table, off_table, naked_table],
        sources=sources(), flow=flow,
        finding_figures={'g': G}, finding_allow=('FY2026',))


def render():
    p = page(data())
    p['not_established'] = [
        'Which lines the $500,000 added after the budget vote went to.',
        'That the $500,000 is the free cash article the minutes name.',
        'Which document codes each line correctly.',
        'That a line matched by amount is the same line on both sides.',
        'Why the kindergarten aide accounts carried no budget.',
    ]
    return json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('budget against MUNIS: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
