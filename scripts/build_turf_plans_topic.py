#!/usr/bin/env python3
"""The turf field in the capital plans, fiscal year by fiscal year.

    python3 scripts/build_turf_plans_topic.py           # write the topic payload
    python3 scripts/build_turf_plans_topic.py --check   # fail if it would change

TJ, 21 October 2026, on the turf field thread: *"can you actually create a related report for
this thread on the per FY capital plan timelines? Basically the table for each FY"* -- after
the rounds tables made plain which year's money each vote was about, and after the boards
were found arguing about a history none of them had in front of them.

THE DATA is sources/data/capital-plan-field-lines.csv: every line about the field in every
capital plan the archive holds, each with a verbatim quote from the document's extracted text
and the fiscal year read off the table's own column (the column method is in each row's
`note`). It was compiled by an isolated agent; this script re-checks every row it uses --
the quote is in the text, the amount is in the quote -- and refuses otherwise.

THE CURATION is VERSIONS below: one copy of each plan version, in date order. The archive
holds several byte-identical or re-saved copies (a pdf and a pptx of one deck, the Finance
Committee's copy of the Town Manager's presentation); counting each would double a plan.

What a plan line IS, and is not: a figure a department or the Town Manager PROPOSED for a
year. Not an appropriation, not a vote of Town Meeting, not money spent (rule 7). The plans
are documents a person assembled -- `stated`, in rule 13a's terms -- and the table says so.
"""
import argparse
import csv
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402

TID = 'turf-field-capital-plans'
ME = os.path.basename(__file__)
DATA = os.path.join(ROOT, 'sources', 'data', 'capital-plan-field-lines.csv')
PUB = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', 'capital-plan-field-lines.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % TID)

# (key, plan_id in the CSV, x label, who, [(fy or None, words in the printed item)]).
# An empty list is a plan read page by page with NO field line (the CSV's own row says which
# pages). Dates come from the CSV, never from here.
VERSIONS = [
    ('tm22', 'town-fy22', 'Town Manager FY22', 'Town Manager', [(2027, 'Retaining')]),
    ('tm23', 'town-fy23', 'Town Manager FY23', 'Town Manager', [(2025, 'Retaining')]),
    ('sc24', 'schools-fy24-fy33', 'Schools FY24', 'Schools', [(2024, 'Feasibility'), (None, 'Upgrade')]),
    ('tm24', 'town-fy24', 'Town Manager FY24', 'Town Manager',
     [(2024, 'Feasibility'), (2025, 'Engineered'), (2026, 'Upgrade')]),
    ('sc25d', 'schools-fy25-draft', 'Schools FY25 draft', 'Schools',
     [(2025, 'Upgrade'), (2026, 'Upgrade'), (2027, 'Upgrade')]),
    ('sc25', 'schools-fy25-fy34', 'Schools FY25', 'Schools',
     [(2025, 'Site Survey'), (2026, 'Site Survey'), (2027, 'Site Survey')]),
    ('tm25', 'town-fy25-preliminary', 'Town Manager FY25', 'Town Manager', [(2025, 'Site Survey')]),
    ('sc26', 'schools-fy26-fy35-approved', 'Schools FY26', 'School Committee',
     [(2027, 'LPS20-04-C: Hillside'), (2027, 'LPS20-04-C: Track')]),
    ('tm26', 'town-fy26-preliminary', 'Town Manager FY26', 'Town Manager', []),
    ('sc27', 'schools-fy27-fy35-revised-draft', 'Schools FY27 draft', 'Schools',
     [(2027, 'LMHS Turf Field: Hillside'), (2029, 'LMHS Turf Field: Track')]),
    ('tm27', 'town-fy27-preliminary', 'Town Manager FY27', 'Town Manager', []),
]
# The year each Town Manager program is FOR -- its title says so; a program with no field
# line is shown as "no field line" in that year's table.
PROGRAM_FY = {'tm26': 2026, 'tm27': 2027}


def fail(msg):
    raise SystemExit('build_turf_plans_topic: ' + msg)


def squash(s):
    return re.sub(r'\s+', '', (s or '').replace('’', "'")).lower()


def amount(s):
    """The printed amount as dollars: '$1.2 million', '$1.5 M', '1,200,000', '$2,000,000.00'."""
    t = s.replace('$', '').replace(',', '').strip().lower()
    m = re.fullmatch(r'([\d.]+)\s*(million|m)?\*?', t)
    if not m:
        return None
    v = float(m.group(1)) * (1e6 if m.group(2) else 1)
    return int(round(v))


def load():
    rows = list(csv.DictReader(open(DATA, encoding='utf-8')))
    by_plan = {}
    for r in rows:
        by_plan.setdefault(r['plan_id'], []).append(r)
    texts = {}
    versions = []
    for key, pid, x, who, want in VERSIONS:
        rs = by_plan.get(pid)
        if not rs:
            fail('plan %s is not in %s' % (pid, os.path.relpath(DATA, ROOT)))
        r0 = rs[0]
        lines = []
        for fy, words in want:
            hit = [r for r in rs if (str(fy) if fy else '') == r['fy'] and words.lower() in r['item'].lower()]
            if not hit:
                fail('%s: no line for %s matching %r' % (pid, fy, words))
            vals = {amount(r['amount']) for r in hit}
            if len(vals) != 1:
                fail('%s: lines for %s matching %r disagree: %s' % (pid, fy, words, vals))
            lines.append(hit[0])
        if not want and any(r['amount'] for r in rs):
            fail('%s is curated as having no field line but the data has one' % pid)
        for r in (lines or rs[:1]):
            txt = os.path.join(ROOT, r['text'])
            if txt not in texts:
                if not os.path.exists(txt):
                    fail('no text at %s' % r['text'])
                texts[txt] = squash(open(txt, encoding='utf-8', errors='replace').read())
            if squash(r['quote']) not in texts[txt]:
                fail('%s: quote not in %s: %r' % (pid, r['text'], r['quote'][:60]))
            if r['amount'] and squash(r['amount']) not in squash(r['quote']):
                fail('%s: amount %r not in its quote' % (pid, r['amount']))
            if not os.path.exists(os.path.join(ROOT, 'sources', r['doc'])):
                fail('%s: document not held: %s' % (pid, r['doc']))
        # LEFT OUT OF THE RECOMMENDATION: a Town Manager program prints the requests it did NOT
        # recommend on a page of their own ("Capital Requests Not Included in Preliminary ...
        # Recommendation"). A line found there was asked for and left out -- shown as a plain
        # amount it would read as funded. The page's heading must be in the document's text.
        def left_out(ln):
            for r in rs:
                if (r['fy'] == ln['fy'] and amount(r['amount']) == amount(ln['amount'])
                        and 'not included' in r['note'].lower()):
                    if 'notincluded' not in texts[os.path.join(ROOT, r['text'])]:
                        fail('%s: a "Not Included" page is cited and not in the text' % pid)
                    return True
            return False
        versions.append(dict(key=key, pid=pid, x=x, who=who, date=r0['plan_date'], title=r0['plan_title'],
                             doc=r0['doc'],
                             lines=[dict(fy=int(r['fy']) if r['fy'] else None, item=r['item'],
                                         printed=r['amount'], usd=amount(r['amount']),
                                         left_out=left_out(r)) for r in lines]))
    # THE FINDING'S SCOPE, checked on every schools' plan held -- not only the curated ones.
    for pid, rs in by_plan.items():
        if rs[0]['made_by'] in ('schools-request', 'school-committee-approved') and not any(r['amount'] for r in rs):
            fail('%s is a schools plan with no field line; the finding says every one has it' % pid)
    return versions


def short(x):
    """'Town Manager FY24' -> 'TM FY24'; 'Schools FY25 draft' -> 'Sch FY25 d': ten bars share a phone."""
    return re.sub(r'^(Town Manager|Schools) FY(\d\d)( draft)?$',
                  lambda m: ('TM' if m.group(1) == 'Town Manager' else 'S') + m.group(2) + ('d' if m.group(3) else ''), x)


def month(iso):
    import datetime as dt
    return dt.date.fromisoformat(iso).strftime('%b %Y') if iso else 'undated'


def build():
    V = load()
    by = {v['key']: v for v in V}
    years = sorted({ln['fy'] for v in V for ln in v['lines'] if ln['fy']})
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    U = lambda v: figure(v, C.usd(v))

    def line(key, fy, words=''):
        hits = [ln for ln in by[key]['lines'] if ln['fy'] == fy and words.lower() in ln['item'].lower()]
        if len(hits) != 1:
            fail('expected one %s line for %s %r' % (key, fy, words))
        return hits[0]['usd']

    # ------------------------------------------------------------------ the measurements
    schools = [v for v in V if v['who'] != 'Town Manager']
    if not all(v['lines'] for v in schools):
        fail('a schools plan with no field line; the finding says every one has it')
    first_fy = 2022
    if V[0]['pid'] != 'town-fy22':
        fail('the earliest plan with the field is no longer the FY2022 program')
    # the year of each plan's LARGEST dated line -- where the big money sat
    big = []
    for v in V:
        dated = [ln for ln in v['lines'] if ln['fy'] and ln['usd']]
        if dated and max(ln['usd'] for ln in dated) >= 1_000_000:
            big.append(max(dated, key=lambda ln: ln['usd'])['fy'])
    moves = [y for i, y in enumerate(big) if i == 0 or y != big[i - 1]]
    if len(moves) < 3:
        fail('the big money no longer moves between at least three years: %s' % moves)
    sc26 = line('sc26', 2027, 'Hillside') + line('sc26', 2027, 'Track')
    turf26 = line('sc26', 2027, 'Track')
    turf27 = line('sc27', 2029, 'Track')
    hard27 = line('sc27', 2027, 'Hillside')
    none_tm = [k for k in ('tm26', 'tm27') if not by[k]['lines']]
    if none_tm != ['tm26', 'tm27']:
        fail('the Town Manager FY26 and FY27 programs are no longer both without the field')

    f, con = LD.fact, TP.conclusion
    facts = [
        f('wall', U(line('tm22', 2027)), 'retaining wall repairs, the first plan line we hold', 'published'),
        f('study', U(line('tm24', 2024)), 'feasibility study for %s, left out of the program' % C.fy(2024),
          'published', {'y': F(2024)}),
        f('big24', U(line('tm24', 2026)), 'walls, drainage and turf, set in %s' % C.fy(2026), 'published',
          {'y': F(2026)}),
        f('sc26', U(sc26), 'School Committee’s plan, all in %s' % C.fy(2027), 'published', {'y': F(2027)}),
        f('turf26', U(turf26), 'track and turf replacement, that plan', 'published'),
        f('turf27', U(turf27), 'track and turf, next year’s draft, moved to %s' % C.fy(2029), 'published',
          {'y': F(2029)}),
        f('hard27', U(hard27), 'hillside and drainage, still in %s' % C.fy(2027), 'published', {'y': F(2027)}),
        f('tm-none', figure(len(none_tm), C.num(len(none_tm)), 'programs'),
          'Town Manager programs, %s and %s: no field line' % (C.fy(2026), C.fy(2027)), 'published',
          {'a': F(2026), 'b': F(2027)}),
    ]
    yrs = {'a': F(moves[0]), 'b': F(moves[1]), 'c': F(moves[-1])}
    conclusions = [
        con('Every one of the schools’ own capital plans we hold lists the field, from %s on.' % C.fy(first_fy),
            ['wall', 'sc26', 'turf27'], {'y': F(first_fy)}),
        con('Its biggest line was set for %s, then %s, then %s.' % (C.fy(moves[0]), C.fy(moves[1]), C.fy(moves[-1])),
            ['big24', 'sc26', 'turf27'], yrs),
        con('Track and turf was %s for %s; the next year’s draft made it %s for %s.'
            % (C.usd(turf26), C.fy(2027), C.usd(turf27), C.fy(2029)),
            ['turf26', 'turf27'], {'a': U(turf26), 'b': U(turf27), 'y': F(2027), 'z': F(2029)}),
        con('The Town Manager’s programs for %s and %s list no field line.' % (C.fy(2026), C.fy(2027)),
            ['tm-none'], {'a': F(2026), 'b': F(2027)}),
    ]

    # ------------------------------------------------------------------ the chart
    charted = [v for v in V if all(ln['fy'] for ln in v['lines'])]
    chart = TP.series(
        'Where each plan put the field',
        [short(v['x']) for v in charted],
        [TP.track(C.fy(y), [sum(ln['usd'] or 0 for ln in v['lines'] if ln['fy'] == y) or None for v in charted],
                  basis='stated') for y in years],
        '$', kind='bar', stacked=True,
        note='One bar per plan, oldest first, coloured by the year it put the money in. TM: Town Manager; '
             'S: schools; d: draft; the number is the plan’s own year.')

    # ------------------------------------------------------------------ the tables
    def label(v):
        return '%s, %s' % (v['x'], month(v['date']))

    def cell(v, y):
        ls = [ln for ln in v['lines'] if ln['fy'] == y]
        if ls:
            return ' + '.join((C.usd(ln['usd']) if ln['usd'] else ln['printed'])
                              + (' (left out)' if ln['left_out'] else '') for ln in ls)
        if PROGRAM_FY.get(v['key']) == y:
            return 'no field line'
        return ''
    cols = [C.fy(y) for y in years] + ['No single year']
    views = [dict(key='all', label='Every plan', total_col=None, kinds=['stated'] * len(cols), columns=cols,
                  rows=[dict(label=label(v), cells=[cell(v, y) for y in years]
                             + [' + '.join(C.usd(ln['usd']) for ln in v['lines'] if not ln['fy'])])
                        for v in V],
                  note='Each row one plan version, oldest first, as printed. A plan line is a proposal for '
                       'that year, not money voted or spent. One schools deck gave its main figure no single year. Left out: listed on the Town Manager’s own '
                       'page of requests not included in the program.')]
    for y in years:
        rows = []
        for v in V:
            ls = [ln for ln in v['lines'] if ln['fy'] == y]
            for ln in ls:
                rows.append(dict(label=label(v), cells=[v['who'], ln['item'],
                                                         C.usd(ln['usd']) if ln['usd'] else ln['printed'],
                                                         'left out of the program' if ln['left_out'] else '']))
            if not ls and PROGRAM_FY.get(v['key']) == y:
                rows.append(dict(label=label(v), cells=[v['who'], 'no field line', '', '']))
        views.append(dict(key='fy%d' % y, label=C.fy(y), total_col=None, kinds=['stated'] * 4,
                          columns=['Who', 'The line, as printed', 'Amount', 'Status'], rows=rows,
                          note='Every plan that put field money in %s, oldest first.' % C.fy(y)))
    table = dict(caption='The field, plan by plan and year by year', views=views)

    # ------------------------------------------------------------------ sources
    sources = [dict(label='%s — %s (%s)' % (v['who'], ' '.join(v['title'].split()), month(v['date'])),
                    href='/docs/' + v['doc']) for v in V]
    sources.append(dict(label='Lunenburg Budget Project — capital-plan-field-lines.csv (every field line in '
                              'every capital plan held, with its quote and how its year was read)',
                        href='/docs/data/capital-plan-field-lines.csv'))

    return TP.page(
        TID,
        'The schools have put the field in every capital plan of theirs since %s; its year kept moving.'
        % C.fy(first_fy),
        facts, conclusions, chart=chart, table=table, sources=sources,
        finding_figures={'y': F(first_fy)})


def output():
    return json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if REG.TOPICS.get(TID, (None, None, None))[2] != ME:
        fail('%s is not registered to %s in scripts/topic_registry/' % (TID, ME))
    text = output()
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        pub = open(PUB, 'rb').read() if os.path.exists(PUB) else None
        if cur != text or pub != open(DATA, 'rb').read():
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('turf field capital plans topic: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    shutil.copyfile(DATA, PUB)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
