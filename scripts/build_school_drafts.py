#!/usr/bin/env python3
"""ONE PAGE PER SCHOOL BUDGET DRAFT, line by line -- every version the district prints.

    python3.11 scripts/build_school_drafts.py           # write one topic payload per draft
    python3.11 scripts/build_school_drafts.py --check   # fail if any would change

TJ, 20 November 2026: "we need to ingest it to put it in the DB ... something like
/school-budget-fy28-draft1 and theres a link to it on the budget feed version and on other report
pages under the school hub" -- and "AND comparing version over version to shows diffs too".

Reads only `sources/data/budget-seasons/fy28-draft-lines.csv`, which
scripts/extract_fy28_draft_lines.py writes for a draft only once it foots (rule 13). Nothing here
names a document or a version: a draft that arrives in that table gets a page on the next run, at
`/school-all-funds/school-budget-fy<NN>-version-<N>`, also answered at the short
`/school-budget-fy<NN>-version-<N>` (fy28/src/routes.ts). When a draft has a predecessor, its page
leads its second section with what changed line by line since that one.

`drafts()` is also what scripts/build_budget_season.py reads to link each version card to its
page and to say on the card what changed. One reading of the rows, so the card and the page
cannot disagree (rule 7d).

Rule 1: the FY26 actual column is printed in the line list for reference and feeds no headline.
Rule 11: every figure is a net appropriation, not what anything costs.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402

LINES = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28-draft-lines.csv')
FOOTING = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28-draft-lines.footing.csv')
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
INDEX_OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-drafts.json')
HOME = 'school-all-funds'
TOP_STEPS = 6          # the bridge: the largest increases by line, then every other line as one step
DOWN_ROWS = 10


def fail(msg):
    raise SystemExit('build_school_drafts: ' + msg)


def page_id(fy, version):
    return 'school-budget-fy%02d-version-%d' % (fy % 100, version)


def short_path(fy, version):
    return '/' + page_id(fy, version)


def f(v):
    return float(v) if v not in ('', None) else None


def z(v):
    return v or 0.0


def key(r):
    """A line's identity across drafts. The cost center CODE, not its printed name, so a heading
    reworded between versions does not turn every line under it into a removal and an addition."""
    return (r['section'], r['cost_center'], r['line'], r['ordinal'])


def read():
    out = OrderedDict()
    for r in csv.DictReader(open(LINES, encoding='utf-8')):
        for c in ('fy26_original', 'fy26_actual', 'fy27_budget', 'fy28_proposed', 'diff'):
            r[c] = f(r[c])
        r['fy'], r['version'], r['page'] = int(r['fy']), int(r['version']), int(r['page'])
        out.setdefault((r['fy'], r['version']), []).append(r)
    return out


def footing():
    out = defaultdict(list)
    if os.path.exists(FOOTING):
        for r in csv.DictReader(open(FOOTING, encoding='utf-8')):
            out[(int(r['fy']), int(r['version']))].append(r)
    return out


def changed(prev, cur):
    """Line by line, `cur` against `prev`, both on the FY28 proposed column: [(kind, row, before,
    after)] for every line added, removed, up or down. Computed from the rows; nothing typed."""
    p = {key(r): r for r in prev}
    c = {key(r): r for r in cur}
    out = []
    for k, r in c.items():
        a = z(r['fy28_proposed'])
        if k not in p:
            if a:
                out.append(('added', r, 0.0, a))
            continue
        b = z(p[k]['fy28_proposed'])
        if round(a - b, 2):
            out.append(('up' if a > b else 'down', r, b, a))
    for k, r in p.items():
        if k not in c and z(r['fy28_proposed']):
            out.append(('removed', r, z(r['fy28_proposed']), 0.0))
    return sorted(out, key=lambda x: -abs(x[3] - x[2]))


def drafts():
    """[{fy, version, id, path, short, document, total, prior_total, change, diff}] for every
    draft in the table, oldest first. `diff` is None for a first draft, else the count and dollars
    of lines added, removed, up and down against the previous version of the same year."""
    D = read()
    out = []
    for (fy, v), rows in D.items():
        prev = D.get((fy, v - 1))
        total = sum(z(r['fy28_proposed']) for r in rows)
        prior = sum(z(r['fy27_budget']) for r in rows)
        d = None
        if prev:
            ch = changed(prev, rows)
            d = {k: dict(n=sum(1 for x in ch if x[0] == k), dollars=round(sum(x[3] - x[2] for x in ch if x[0] == k), 2))
                 for k in ('added', 'removed', 'up', 'down')}
            d['against'] = v - 1
            d['net'] = round(total - sum(z(r['fy28_proposed']) for r in prev), 2)
        sal = [r for r in rows if r['section'] == 'salaries']
        exp = [r for r in rows if r['section'] == 'expenses']
        sp = lambda rs, c: sum(z(r[c]) for r in rs)
        out.append(dict(fy=fy, version=v, id=page_id(fy, v), path='/%s/%s' % (HOME, page_id(fy, v)),
                        short=short_path(fy, v), document=rows[0]['document'], date=published(rows[0]['document']),
                        total=round(total, 2), prior_total=round(prior, 2), change=round(total - prior, 2),
                        salaries=(round(sp(sal, 'fy27_budget'), 2), round(sp(sal, 'fy28_proposed'), 2)),
                        expenses=(round(sp(exp, 'fy27_budget'), 2), round(sp(exp, 'fy28_proposed'), 2)),
                        lines=len(rows), diff=d))
    return out


INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
MONTHS = {m: i + 1 for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july',
                                          'august', 'september', 'october', 'november', 'december'))}


def published(document):
    """The date a draft was put before the committee: the catalogue's meeting date, else the date
    on the superintendent's memo that presents it, else None. Never the day we fetched it."""
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        if r.get('local') == document and r.get('meeting_date'):
            return r['meeting_date']
    memo = document.replace('/docs/', '/text/').replace('-budget-version-', '-school-committee-budget-version-').replace('.pdf', '-memo.txt')
    path = os.path.join(ROOT, memo)
    if os.path.exists(path):
        m = re.search(r'Date:\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})', re.sub(r'\s+', ' ', open(path, encoding='utf-8').read()))
        if m and m.group(1).lower() in MONTHS:
            return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1).lower()], int(m.group(2)))
    return None


def label_of(r, dup):
    n = r['line']
    return '%s (%s)' % (n, r['cost_center_name']) if dup[n] > 1 else n


def page(fy, v, rows, prev, foot):
    pid = page_id(fy, v)
    fy_prior = fy - 1
    U = lambda x: figure(x, C.usd(x), 'dollars')
    P = lambda x: figure(x, C.pct(x), 'percent')
    N = lambda n, unit: figure(n, C.num(n), unit)
    tot = sum(z(r['fy28_proposed']) for r in rows)
    pri = sum(z(r['fy27_budget']) for r in rows)
    inc = tot - pri
    if pri <= 0:
        fail('%s: no FY%d budget column' % (pid, fy_prior))
    pct = 100 * inc / pri
    for r in rows:
        r['_d'] = z(r['fy28_proposed']) - z(r['fy27_budget'])
    dup = defaultdict(int)
    for r in rows:
        dup[r['line']] += 1
    doc = rows[0]['document']
    doc_href = '/docs/' + doc[len('sources/'):]
    memo = doc.replace('-budget-version-', '-school-committee-budget-version-').replace('.pdf', '-memo.pdf')
    sources = [dict(key='draft', label='Lunenburg Public Schools — FY%d budget, version %d, line by line' % (fy, v),
                    href=doc_href)]
    if os.path.exists(os.path.join(ROOT, memo)):
        sources.append(dict(key='memo', label='Superintendent’s memo presenting version %d' % v,
                            href='/docs/' + memo[len('sources/'):]))
    sources += [dict(key='lines', label='Every line of every draft, as we read it (our extract)',
                     href='/docs/data/budget-seasons/fy28-draft-lines.csv'),
                dict(key='footing', label='How each draft was checked against its printed totals (ours)',
                     href='/docs/data/budget-seasons/fy28-draft-lines.footing.csv')]
    if prev:
        sources.append(dict(key='prev', label='Lunenburg Public Schools — FY%d budget, version %d, line by line' % (fy, v - 1),
                            href='/docs/' + prev[0]['document'][len('sources/'):]))
    srcs = [s['key'] for s in sources]
    cite = TP.cite
    con = TP.conclusion
    fact = LD.fact
    facts, cons, flow = [], [], ['finding']
    Fy = lambda y: figure(y, C.fy(y), 'fiscal year')

    # ---- the signature: from last year's budget to this draft, by the lines that moved most
    up = sorted([r for r in rows if r['_d'] > 0], key=lambda r: -r['_d'])
    top = up[:TOP_STEPS]
    # THE REST, SPLIT BY WHAT IT IS. TJ, 21 November 2026: "a 1.2m 'Everything else' line is
    # surprising and confusing". One step for 303 lines hid that 46 of them FELL; so the rest is
    # three steps -- the other salary lines that rose, the other lines that rose, the lines that
    # fell -- each with its count in the label. They still carry the bridge to the cent.
    named = {id(r) for r in top}
    others = [r for r in rows if id(r) not in named]
    sal_up = [r for r in others if r['_d'] > 0 and r['section'] == 'salaries']
    oth_up = [r for r in others if r['_d'] > 0 and r['section'] != 'salaries']
    fell = [r for r in others if r['_d'] < 0]
    rest_steps = [(lab, grp) for lab, grp in (
        ('%s more salary lines, up' % C.num(len(sal_up)), sal_up),
        ('%s more lines outside salaries, up' % C.num(len(oth_up)), oth_up),
        ('%s lines that fell' % C.num(len(fell)), fell)) if grp]
    steps = [(label_of(r, dup), round(r['_d'], 2)) for r in top] + \
            [(lab, round(sum(r['_d'] for r in grp), 2)) for lab, grp in rest_steps]
    if abs(sum(x[1] for x in steps) - inc) > 0.05:
        fail('%s: the bridge steps do not carry the FY%d budget to the draft' % (pid, fy_prior))
    bridge = TP.bridge('From last year’s budget to this draft',
                       ('%s budget' % C.fy(fy_prior), round(pri, 2)), steps,
                       ('Version %d' % v, round(tot, 2)), '$',
                       note='The six lines that rose most, then every other line by whether it rose or fell.')
    top_sum = sum(r['_d'] for r in top)
    share = 100 * top_sum / inc
    facts += [fact('total', U(tot), 'version %d, %s' % (v, C.fy(fy)), 'published',
                   label_figures={'v': N(v, 'version'), 'y': Fy(fy)}),
              fact('increase', U(inc), 'more than the %s budget' % C.fy(fy_prior), 'published',
                   label_figures={'y': Fy(fy_prior)}),
              fact('top', U(top_sum), 'added by the six lines that rose most', 'published'),
              fact('share', P(share), 'of the increase, from those six lines', 'published')]
    cons.append(con('Six of %s lines carry %s of the %s increase.' % (C.num(len(rows)), C.pct(share), C.usd(inc)),
                    ['total', 'increase', 'top', 'share'],
                    {'n': N(len(rows), 'lines'), 's': P(share), 'i': U(inc)}, allow=('Six',),
                    so='Most of the request turns on the six lines drawn above; any change to them moves the total.'))
    flow += [cite(('chart', 0), *[k for k in ('draft', 'memo') if k in srcs]), ('conclusion', len(cons) - 1)]

    # ---- what changed since the previous version (only once there is one)
    also = []
    if prev:
        ch = changed(prev, rows)
        # Ranked by how far each moved, and each label says which way: a ranking draws magnitudes.
        WAY = dict(up='up', down='down', added='new', removed='removed')
        lab = lambda x: '%s · %s' % (x[1]['line'], WAY[x[0]])
        moved = ch[:15]
        rk = TP.ranking('Lines changed since the previous version',
                        [(lab(x), round(abs(x[3] - x[2]), 2)) for x in moved], '$',
                        note='How far each moved: the %s largest of %s lines that changed, on the proposed column.'
                             % (C.num(len(moved)), C.num(len(ch))),
                        note_figures={'a': N(len(moved), 'lines'), 'b': N(len(ch), 'lines')})
        also.append(rk)
        net = tot - sum(z(r['fy28_proposed']) for r in prev)
        facts += [fact('vchanged', N(len(ch), 'lines'), 'lines changed since version %d' % (v - 1), 'published',
                       label_figures={'v': N(v - 1, 'version')}),
                  fact('vnet', U(net), 'net change since version %d' % (v - 1), 'published',
                       label_figures={'v': N(v - 1, 'version')})]
        cons.append(con('%s lines changed since version %s, a net %s.' % (C.num(len(ch)), C.num(v - 1), C.usd(net)),
                        ['vchanged', 'vnet'], {'n': N(len(ch), 'lines'), 'v': N(v - 1, 'version'), 'd': U(net)},
                        so='The draft is being revised line by line; the list below names every move.'))
        flow += [cite(('chart', 1), 'draft', 'prev'), ('conclusion', len(cons) - 1)]

    # ---- salaries against everything else, the district's own two totals
    sal = [r for r in rows if r['section'] == 'salaries']
    exp = [r for r in rows if r['section'] == 'expenses']
    res = [r for r in rows if r['section'] == 'reserve']
    s27, s28 = sum(z(r['fy27_budget']) for r in sal), sum(z(r['fy28_proposed']) for r in sal)
    e27, e28 = sum(z(r['fy27_budget']) for r in exp), sum(z(r['fy28_proposed']) for r in exp)
    sp, ep = 100 * (s28 - s27) / s27, 100 * (e28 - e27) / e27
    card = lambda name, a, b, p: TB.panel(name, [(('%s budget' % C.fy(fy_prior), None, (C.fy(fy_prior),)), C.usd(a), None),
                                                 (('Version %d' % v, None, (str(v),)), C.usd(b), None),
                                                 ('Change', '%s (%s)' % (C.usd(b - a), C.pct(p)), 'bad' if b > a else 'good')])
    pan = TB.panels('Salaries and everything else',
                    [card('Salaries', s27, s28, sp), card('Everything else', e27, e28, ep)],
                    note=('The district’s own two totals. The Salary Reserve, %s, is printed in neither.'
                          % C.usd(sum(z(r['fy28_proposed']) for r in res)), None,
                          (C.usd(sum(z(r['fy28_proposed']) for r in res)),)),
                    so='The split is the district’s own: which lines count as salaries is how its book is laid out.')
    facts += [fact('salpct', P(sp), 'salaries, rise on the %s budget' % C.fy(fy_prior), 'published',
                   label_figures={'y': Fy(fy_prior)}),
              fact('exppct', P(ep), 'everything else, rise on the %s budget' % C.fy(fy_prior), 'published',
                   label_figures={'y': Fy(fy_prior)})]
    cons.append(con('Everything but salaries rises %s; salaries rise %s.' % (C.pct(ep), C.pct(sp)),
                    ['exppct', 'salpct'], {'e': P(ep), 's': P(sp)},
                    so='The non-salary side grows faster, though salaries remain the larger part.'))
    flow += [cite(pan, 'draft'), ('conclusion', len(cons) - 1)]

    # ---- the lines below last year's budget
    down = sorted([r for r in rows if r['_d'] < 0], key=lambda r: r['_d'])
    if down:
        dsum = -sum(r['_d'] for r in down)
        rk = TP.ranking('Lines below last year’s budget',
                        [(label_of(r, dup), round(-r['_d'], 2)) for r in down[:DOWN_ROWS]], '$',
                        note='How far each line falls short of its %s budget; the %s largest of %s.'
                             % (C.fy(fy_prior), C.num(min(DOWN_ROWS, len(down))), C.num(len(down))),
                        note_figures={'y': Fy(fy_prior), 'a': N(min(DOWN_ROWS, len(down)), 'lines'),
                                      'b': N(len(down), 'lines')})
        also.append(rk)
        facts += [fact('down', N(len(down), 'lines'), 'lines below the %s budget' % C.fy(fy_prior), 'published',
                       label_figures={'y': Fy(fy_prior)}),
                  fact('downsum', U(dsum), 'less, across those lines', 'published')]
        cons.append(con('%s lines come in below %s, together %s less.' % (C.num(len(down)), C.fy(fy_prior), C.usd(dsum)),
                        ['down', 'downsum'], {'n': N(len(down), 'lines'), 'y': Fy(fy_prior), 'd': U(dsum)},
                        so='A lower line may be a cut, a move to another line or a re-estimate; the draft does not say.'))
        flow += [cite(('chart', len(also)), 'draft'), ('conclusion', len(cons) - 1)]

    # ---- every line, by cost center
    new = [r for r in rows if not z(r['fy27_budget']) and z(r['fy28_proposed'])]
    zero = [r for r in rows if z(r['fy27_budget']) and not z(r['fy28_proposed'])]
    figs, allow = set(), set()
    groups = OrderedDict()
    for r in rows:
        g = groups.setdefault((r['section'], r['cost_center'], r['cost_center_name']), [])
        g.append(r)

    def money(x):
        s = C.usd(x) if x is not None else ''
        if s:
            figs.add(s)
        return s

    def signed(x):
        s = ('+' if x > 0 else '') + C.usd(x) if round(x) else '—'
        figs.add(s)
        figs.add(C.usd(x))
        return s
    def pctof(prior, change):
        """The change as a percent of the FY27 budget: ours, from the two amounts. None where FY27 was
        zero -- a line new this year has no rate, and the list says 'new' rather than an infinity."""
        if not prior:
            return None, ('new' if round(change) else '—')
        p = 100 * change / prior
        t = '—' if not round(change) else ('+' if p > 0 else '') + C.pct(p)
        figs.add(t)
        return round(p, 4), t
    SEC = dict(expenses='Everything else', salaries='Salaries', reserve='Reserve')
    gl = []
    for (sec, cc, name), ls in groups.items():
        allow.update(x for x in (cc, name) if x)
        d = sum(r['_d'] for r in ls)
        lines = []
        for r in ls:
            allow.add(r['line'])
            tag = 'new' if r in new else ('zero' if r in zero else '')
            pv, pt = pctof(z(r['fy27_budget']), r['_d'])
            lines.append(dict(line=r['line'], actual=money(r['fy26_actual']), prior=money(r['fy27_budget']),
                              proposed=money(r['fy28_proposed']), change=signed(r['_d']), n=round(r['_d'], 2),
                              # the values each column sorts on: numbers, not prose (rule 2 checks strings)
                              v=[r['fy26_actual'], r['fy27_budget'], r['fy28_proposed'], round(r['_d'], 2), pv],
                              pct=pt, tag=tag, page=r['page']))
        gpv, gpt = pctof(sum(z(r['fy27_budget']) for r in ls), d)
        gl.append(dict(section=SEC[sec], code=cc, name=name or SEC[sec], prior=money(sum(z(r['fy27_budget']) for r in ls)),
                       proposed=money(sum(z(r['fy28_proposed']) for r in ls)), change=signed(d), n=round(d, 2),
                       v=[round(sum(z(r['fy26_actual']) for r in ls), 2), round(sum(z(r['fy27_budget']) for r in ls), 2),
                          round(sum(z(r['fy28_proposed']) for r in ls), 2), round(d, 2), gpv],
                       pct=gpt, lines=lines))
    for g in gl:
        figs.update([g['prior'], g['proposed']])
    figs.discard('')
    text = dict(line='Line', actual='%s actual' % C.fy(fy - 2), prior='%s budget' % C.fy(fy_prior),
                proposed='Version %d' % v, change='Change', pct='% change', all='All lines', up='Up', down='Down',
                new='New this year', zero='To zero', expand='Show every cost center', collapse='Fold them',
                grouped='Group by cost center', sort_hint='Click a column to sort; again to reverse.',
                search='Find a line, e.g. health insurance', none='No line matches.',
                show_all='Show every line', fewer='Show fewer',
                cost_center='Cost center',
                actual_note='The %s actual is what was spent, printed for reference; nothing on this page is '
                            'measured from it.' % C.fy(fy - 2),
                page='page')
    allow.update([C.fy(fy - 2), C.fy(fy_prior), 'Version %d' % v, 'page'])
    lines_block = TB.custom('school-draft-lines', 'Every line, largest change first',
                            dict(groups=gl, text=text, counts=dict(new=len(new), zero=len(zero))),
                            place='body', figures=sorted(figs), allow=sorted(allow),
                            so='Each line is what the town would appropriate for it, net of grants and fees, not its cost.')
    flow.append(cite(lines_block, 'draft', 'lines'))
    if not prev and new:
        nsum = sum(z(r['fy28_proposed']) for r in new)
        facts += [fact('new', N(len(new), 'lines'), 'lines new this year', 'published'),
                  fact('newsum', U(nsum), 'proposed for those new lines', 'published')]
        cons.append(con('%s lines are new this year, %s in all.' % (C.num(len(new)), C.usd(nsum)),
                        ['new', 'newsum'], {'n': N(len(new), 'lines'), 'd': U(nsum)},
                        so='Each is marked New this year in the list above.'))
        flow.append(('conclusion', len(cons) - 1))

    # ---- how it was checked: the footing record, one row per identity
    rows_t = []
    COLN = dict(fy26_original='%s original' % C.fy(fy - 2), fy26_actual='%s actual' % C.fy(fy - 2),
                fy27_budget='%s budget' % C.fy(fy_prior), fy28_proposed='Version %d' % v, diff='$ Diff')
    for x in foot:
        if x['printed'] == '':
            rows_t.append(dict(label=x['check'], cells=['', '', '', x['result']]))
            continue
        rows_t.append(dict(label='%s — %s' % (x['check'], COLN.get(x['column'], x['column'])),
                           cells=['$%s' % format(float(x['lines_sum']), ',.2f'), '$%s' % format(float(x['printed']), ',.2f'),
                                  '$%s' % format(abs(float(x['difference'])), ',.2f'), x['result']]))
    table = dict(caption='How this draft was checked', views=[dict(
        key='footing', label='Against its own printed totals', kinds=['published'] * 4,
        columns=['Lines add to', 'Printed', 'Difference', 'Result'], rows=rows_t,
        note='The district prints no total per cost center, so each section and the whole are checked. '
             'A printed defect is the district’s reprint of a past year disagreeing with itself.')])
    flow += [cite(('table', 0), 'footing', 'draft'), 'sources']

    finding = 'Version %d asks %s for %s, %s (%s) more than the %s budget.' % (
        v, C.usd(tot), C.fy(fy), C.usd(inc), C.pct(pct), C.fy(fy_prior))
    return TP.page(pid, finding, facts, cons, chart=bridge, table=table, sources=sources,
                finding_figures={'v': N(v, 'version'), 't': U(tot), 'y': Fy(fy), 'i': U(inc), 'p': P(pct),
                                 'q': Fy(fy_prior)},
                also=tuple(also), flow=flow,
                draft=dict(title='FY%02d school budget, version %d' % (fy % 100, v), home=HOME))


def index_json():
    """/data/school-drafts.json: the door on the School Committee's finance page, newest first."""
    ds = sorted(drafts(), key=lambda d: (-d['fy'], -d['version']))
    return json.dumps(dict(source='scripts/build_school_drafts.py', drafts=[
        dict(fy=d['fy'], version=d['version'], path=d['path'], short=d['short'], lines=d['lines'],
             total=C.usd(d['total']), change=('+' if d['change'] >= 0 else '') + C.usd(d['change'])) for d in ds]),
        ensure_ascii=False, sort_keys=True, indent=1) + '\n'


def render_all():
    D = read()
    F = footing()
    out = {}
    for (fy, v), rows in D.items():
        out[page_id(fy, v)] = json.dumps(page(fy, v, rows, D.get((fy, v - 1)), F.get((fy, v), [])),
                                         ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--lines', help='a lines CSV to read instead of the real one (a test fixture)')
    ap.add_argument('--footing', help='its footing CSV')
    ap.add_argument('--out', help='a directory for the payloads instead of fy28/public/data (a test)')
    a = ap.parse_args()
    global LINES, FOOTING, TOPICS, INDEX_OUT
    if a.lines:
        LINES = os.path.abspath(a.lines)
        FOOTING = os.path.abspath(a.footing) if a.footing else FOOTING
    if a.out:
        TOPICS = os.path.join(os.path.abspath(a.out), 'topics')
        INDEX_OUT = os.path.join(os.path.abspath(a.out), 'school-drafts.json')
        os.makedirs(TOPICS, exist_ok=True)
    pages = render_all()
    stale = []
    idx = index_json()
    if a.check:
        if not os.path.exists(INDEX_OUT) or open(INDEX_OUT, encoding='utf-8').read() != idx:
            stale.append('school-drafts.json')
    else:
        open(INDEX_OUT, 'w', encoding='utf-8', newline='\n').write(idx)
    for pid, text in pages.items():
        path = os.path.join(TOPICS, pid + '.json')
        if a.check:
            if not os.path.exists(path) or open(path, encoding='utf-8').read() != text:
                stale.append(pid)
            continue
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, path)
        print('wrote %s' % os.path.relpath(path, ROOT))
    if a.check:
        for s in stale:
            print('STALE %s' % s, file=sys.stderr)
        print('school drafts: %d page(s), %s' % (len(pages), 'current' if not stale else '%d stale' % len(stale)))
        return 1 if stale else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
