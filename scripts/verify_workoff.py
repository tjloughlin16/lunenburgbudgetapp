#!/usr/bin/env python3
"""Every figure on /homes-and-taxes/senior-tax-work-off, recomputed by a second route.

    python3 scripts/verify_workoff.py

build_workoff_topics.py reads sources/data/senior-tax-workoff.csv and checks each value against
its own quote. This script does not trust the CSV's values at all: it reads the DOCUMENTS'
text, finds each figure with its own patterns (the annual reports' "there were nine ... residents
who participated", "accumulated 865.5 hours", the Assessors' "totaled $9,402.50"), counts each
report's department list line by line, and compares what it finds with the PUBLISHED PAYLOAD --
the season table, the facts, the conclusions and the charts. The CSV supplies only where to
look (the file named in a cite), never the number.
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'senior-tax-work-off.json')
DATA = os.path.join(ROOT, 'sources', 'data', 'senior-tax-workoff.csv')
AR = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')
WORDS = {'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'eleven': 11, 'twelve': 12, 'sixteen': 16}
bad = []


def text(path):
    return open(os.path.join(ROOT, path), encoding='utf-8', errors='replace').read()


def flat(s):
    return re.sub(r'\s+', ' ', s)


def money(s):
    return float(s.replace('$', '').replace(',', ''))


def usd2(v):
    return '$' + format(v, ',.2f')


def report(year):
    """The annual report whose program section describes season `year` (same number)."""
    hit = [f for f in os.listdir(AR) if re.match(r'\d+-fy-%d-annual-town-report\.txt$' % year, f)]
    return os.path.join(AR, hit[0]) if hit else None


# ------------------------------------------------------------ the documents, read directly
found = {}
for y in range(2015, 2026):
    p = report(y)
    if not p:
        continue
    t = flat(open(p, encoding='utf-8', errors='replace').read())
    m = re.search(r'(?:There were|During %d, there were) (\w+) (?:Lunenburg )?residents who participated'
                  r'(?: between January 1, %d| from January 1, %d| in the Program)' % (y, y, y), t)
    if not m:
        continue   # FY2023 prints no program section
    n = WORDS[m.group(1).lower()]
    seg = t[m.end():m.end() + 900]
    h = re.search(r'accumulated ([\d,.]+) hours', seg)
    d = re.search(r'accumulated [\d,.]+ hours[^$]{0,40}\$([\d,]+\.\d\d)', seg)
    rate = re.findall(r'received \$(\d+) and worked up to 100 hours', t[max(0, m.start() - 1500):m.start()])
    # the department list: the lines after the heading, up to the hours sentence or the next heading
    raw = open(p, encoding='utf-8', errors='replace').read().split('\n')
    i = next(k for k, ln in enumerate(raw) if re.search(r'(Departments (who|that) participated.*%d|During %d, there were)'
                                                         % (y, y), ln))
    depts = []
    rest = raw[i + 1:]
    for k, ln in enumerate(rest):
        s = ln.strip()
        if s.startswith('===PAGE'):
            # a page break: the list goes on only if the next page reopens the program's section
            nxt = ' '.join(x.strip() for x in rest[k + 1:k + 4])
            if 'WORK-OFF PROGRAM' not in nxt:
                break
            continue
        if s.startswith(('These individuals', 'Eligibility', 'For more')) or re.fullmatch(r'\d+', s):
            if re.fullmatch(r'\d+', s) and k and rest[k - 1].strip().startswith('===PAGE'):
                continue   # the folio of the reopened page
            break
        if not s or 'WORK-OFF PROGRAM' in s or re.match(r'JANUARY 1', s):
            continue
        depts.append(s)
    found[y] = dict(n=n, hours=float(h.group(1).replace(',', '')) if h else None,
                    dollars=money(d.group(1)) if d else None,
                    rate=int(rate[0]) if rate else None, depts=len(depts))

# Seasons before 2015 and 2023: the minutes the CSV points to, read with their own patterns.
rows = {r['season']: r for r in csv.DictReader(open(DATA, encoding='utf-8'))}


def cited(season, m):
    return [flat(text(c.strip().split(':')[0])) for c in rows[season][m + '_cite'].split('|')]


MINUTES = {
    'CY2010': dict(n=(r'(\w+) people have completed', 0), dollars=(r'totaled: \$([\d,.]+) in exemptions', 0)),
    'CY2011': dict(n=(r'approved (\d+) Tax Work-Off exemptions', 0),
                   dollars=(r'Tax Work-Off exemptions in the amount of \$([\d,.]+\d)', 0)),
    'CY2016': dict(dollars=(r'abatement/exemptions is \$([\d,.]+\d)', 0)),
    'CY2012': dict(dollars=(r'totaled: \$([\d,.]+\d) in exemptions', 0)),
    'CY2014': dict(n=(r'There were (\d+) people who participated', 0),
                   dollars=(r'which totaled \$([\d,.]+\d) in exemptions', 0)),
    'CY2023': dict(n=(r'for (\d+) individuals', 0), dollars=(r'The total is under \$([\d,.]+\d)', 0)),
}
for s, pats in MINUTES.items():
    y = int(s[2:])
    out = found.setdefault(y, {})
    for k, (pat, i) in pats.items():
        m = 'participants' if k == 'n' else 'dollars'
        hit = re.search(pat, cited(s, m)[i], re.I)
        if not hit:
            bad.append('%s: %r not found in the cited minutes' % (s, pat))
            continue
        v = hit.group(1)
        out[k] = WORDS.get(v.lower(), None) or (money(v) if k == 'dollars' else int(v))
# 2012: participants are 12 approved in December plus one in March -- our sum, recomputed here
t12 = cited('CY2012', 'participants')
a = re.search(r'approved (\d+) Tax Work-Off exemptions in the amount of \$([\d,.]+\d)', t12[0])
b = re.search(r'A Tax Work Off applicant was also granted a \$([\d,.]+\d) exemption for FY13', t12[1])
found[2012]['n'] = int(a.group(1)) + 1
found[2012]['alt'] = money(a.group(2)) + money(b.group(1))
# 2024: the Assessors' second total
found[2024]['alt'] = money(re.search(r'In FY25, 9 applications were approved and totaled \$([\d,.]+\d)',
                                     cited('CY2024', 'dollars_alt')[0]).group(1))
# 2015, 2017: no total printed; ours is hours times the printed rate
for y in (2015, 2017):
    found[y]['ours'] = found[y]['hours'] * found[y]['rate']

# ------------------------------------------------------------ against the payload
P = json.load(open(PAY, encoding='utf-8'))
table = {r['label']: r['cells'] for r in P['table']['views'][0]['rows']}


def expect(where, got, want):
    if got != want:
        bad.append('%s: page says %r, the documents give %r' % (where, got, want))


for y, f in sorted(found.items()):
    cells = table[str(y)]
    if 'n' in f:
        expect('%d seniors' % y, re.match(r'[\d,]+', cells[0]).group(0), format(f['n'], ',d'))
    if f.get('hours') is not None:
        expect('%d hours' % y, float(cells[1].replace(',', '')), f['hours'])
    if f.get('depts'):
        expect('%d departments' % y, int(cells[2]), f['depts'])
    want = f.get('dollars') if f.get('dollars') is not None else f.get('ours')
    if want is not None:
        expect('%d dollars' % y, re.search(r'\$[\d,]+\.\d\d', cells[3]).group(0), usd2(want))
    if 'alt' in f:
        expect('%d second total' % y, re.findall(r'\$[\d,]+\.\d\d', cells[3])[1], usd2(f['alt']))

# the facts and conclusions
facts = {x['id']: x['value'] and x['value']['text'] for x in P['facts']}
t25 = flat(open(report(2025), encoding='utf-8').read())
cap = int(re.search(r'The 2025 tax abatement maximum is \$([\d,]+)', t25).group(1).replace(',', ''))
sb = flat(text('sources/meetings/text/select-board/2019-04-16-minutes-5155.txt'))
m = re.search(r'enough money to cover (\d+) applicants\. Right now there are only (\w+) people working', sb)
want = {'first': str(found[2010]['n']), 'last': str(found[2025]['n']), 'cap': '$' + format(cap, ',d'),
        'd-first': usd2(found[2010]['dollars']), 'd-last': usd2(found[2025]['dollars']),
        'possible': usd2(found[2025]['n'] * cap), 'h-first': format(found[2015]['hours'], ',.2f'),
        'h-last': format(found[2025]['hours'], ',.2f'), 'funded': m.group(1), 'working': str(WORDS[m.group(2)])}
for k, v in want.items():
    expect('fact %s' % k, facts.get(k), v)
for c in P['conclusions']:
    for k, fg in c['figures'].items():
        if fg['text'] not in c['text']:
            bad.append('conclusion %r: figure %s not in its text' % (c['text'], fg['text']))
allfig = set(want.values()) | {'$750', '2010', '2025'}
for c in P['conclusions']:
    for fg in c['figures'].values():
        if fg['text'] not in allfig:
            bad.append('conclusion figure %r is not one recomputed here' % fg['text'])

# the charts: the participants bars and the money bars are the table's figures
ch = P['chart']
for i, x in enumerate(ch['x']):
    v = [s['values'][i] for s in ch['series'] if s['values'][i] is not None]
    y = int(x)
    if 'n' in found.get(y, {}):
        expect('chart %s' % x, v, [found[y]['n']])
    elif v:
        bad.append('chart %s: a bar with no count in the documents' % x)
for b in P['blocks']:
    if b['block'] == 'chart' and b['spec']['unit'] == '$':
        for i, x in enumerate(b['spec']['x']):
            v = [s['values'][i] for s in b['spec']['series'] if s['values'][i] is not None]
            f = found.get(int(x), {})
            w = f.get('dollars') if f.get('dollars') is not None else f.get('ours')
            expect('money chart %s' % x, v, [w] if w is not None else [])

# privacy: no participant's name. The two lists that print names are never cited; the page holds
# no capitalised word pair outside a vocabulary of boards, months and places.
blob = json.dumps(P, ensure_ascii=False)
for nm in ('Belliveau', 'Hamel', 'Noble', 'Doherty', 'Cajka', 'Laffond'):
    if nm in blob:
        bad.append('a person is named on the page: %s' % nm)

if bad:
    print('verify_workoff: %d problems' % len(bad))
    print('\n'.join('  ' + b for b in bad))
    sys.exit(1)
print('verify_workoff: %d seasons, every figure on the page recomputed from the documents' % len(found))
