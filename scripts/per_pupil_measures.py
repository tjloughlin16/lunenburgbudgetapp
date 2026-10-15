#!/usr/bin/env python3
"""WHAT DESE'S PER-PUPIL FIGURE HOLDS, read once off DESE's own workbook. Shared by the Monty
Tech shelf (build_monty_tech_topics.py) and the School spending shelf's "What per pupil
counts" page, so the two read one set of figures and cannot disagree.

    python3 scripts/per_pupil_measures.py      # print what it read

WHY THIS EXISTS. People in town said *"some districts include their capital projects and
some districts do not"* in per-pupil spending. The answer is in the file, not in anybody's
account of it: DESE's expenditures-by-function workbook carries every district's spending by
function code, FY2009-FY2025, and the per-pupil row (`TTPP`, which DESE titles "Expenditure
(Admin, Instruction, Operations)") is built from those rows. So:

  1. THE CENSUS. Every row of the file is counted by the first character of its function
     code. If no row anywhere carries a 6xxx (community services), 7xxx (fixed assets --
     capital) or 8xxx (debt service) code, the per-pupil figure cannot contain capital or
     debt for ANY district, by construction. That is asserted over all 363,000-odd rows, not
     sampled. A file that starts carrying such rows refuses the build.
  2. THE IDENTITY. Every TTPP row's general fund plus grants/revolving equals its total, to
     DESE's rounding. Asserted for every district and year.
  3. THE EDGE. What the figure DOES count that a reader might call capital: function 2420,
     "Instructional Equipment", and 4300, "Extraordinary Maintenance". Whether districts put
     the same purchase in 2420 or in 7000 cannot be seen in this file -- that is registered
     in money-gaps.csv, never asserted either way (rule 7).

READING THE WORKBOOK TAKES ABOUT A MINUTE AND A HALF, so the extract is cached in the
gitignored build/cache/, keyed by the workbook's sha256. A different workbook is a different
key; nothing is ever read from a cache that does not match the bytes on disk.
"""
import csv
import hashlib
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = 'state-dese/district-expenditures-by-function.xlsx'
PATH = os.path.join(ROOT, 'sources', KEY)
CACHE = os.path.join(ROOT, 'build', 'cache')
# The statewide distribution the rest of the site already publishes (extract_dese_finance.py).
# Read, never recomputed: one median per year on the site, not two. Note it counts a district
# DESE prints at $0 a pupil (Gosnold, which has no pupils of its own) -- see its own docstring.
STATEWIDE = os.path.join(ROOT, 'sources', 'data', 'dese-function-statewide.csv')
LUNENBURG, MONTY = '01620000', '08320000'
# Harvard Public Schools, the district The Bromfield School belongs to: the Bromfield shelf's
# benchmark (build_bromfield_topics.py).
HARVARD = '01250000'
# THE FEDERAL DEFINITION. The Census Bureau's Annual Survey of School System Finances, FY2024,
# in THOUSANDS of dollars (school24doc.docx: "All amounts, except for fall membership and
# personal income, are expressed in thousands of dollars"). Its own NCES ids for the two:
CENSUS_KEY = 'state-census/census-elsec24.xlsx'
CENSUS_PATH = os.path.join(ROOT, 'sources', CENSUS_KEY)
CENSUS_FY = 2024
CENSUS_IDS = {'2507080': LUNENBURG, '2508050': MONTY}
CENSUS_FIELDS = ('NAME', 'UNIT_TYPE', 'V33', 'TOTALEXP', 'TCURELSC', 'NONELSEC', 'TCAPOUT',
                 'F12', 'G15', 'K09', 'K10', 'K11', 'J99', 'L12', 'M12', 'Q11', 'I86')
HEAD = ['SY', 'DIST_CODE', 'DIST_NAME', 'FUNC_CAT_CODE', 'FUNC_CAT_DESC', 'FUNC_CODE',
        'FUNC_DESC', 'IN_OUT_DIST', 'GEN_FUND', 'GRNTS_REVOLV', 'TOT_EXP', 'PER_PUPIL_EXP']
# The function codes on the edge between "counted" and "capital", kept per district and year.
EDGE = ('2420', '4300', '3300', '3400')
VERSION = 4   # bump when the extract's shape changes, so an old cache is not read
# Every row of the districts this site splits line by line, every year: what breakdown() splits.
# Harvard added 15 October 2026 for the Bromfield shelf (VERSION 4).
DETAIL = (LUNENBURG, MONTY, HARVARD)


def fail(msg):
    raise SystemExit('per_pupil_measures: ' + msg)


def _sha(path=PATH):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _read():
    import openpyxl
    ws = openpyxl.load_workbook(PATH, read_only=True).worksheets[0]
    census, ttpp, edge, names, bad, detail = {}, {}, {}, {}, [], {}
    rows = 0
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if i == 1:
            if list(r[:len(HEAD)]) != HEAD:
                fail('%s: the header is no longer %s' % (KEY, HEAD))
            continue
        rows += 1
        fy, lea, code = int(r[0]), r[1], str(r[5])
        census[code[:1]] = census.get(code[:1], 0) + 1
        names.setdefault(lea, r[2])
        if code == 'TTPP':
            gen, gr, tot, pp = r[8], r[9], r[10], r[11]
            if abs((gen or 0) + (gr or 0) - (tot or 0)) > 1:
                bad.append('row %d (%s FY%d): %s + %s != %s' % (i, lea, fy, gen, gr, tot))
            ttpp.setdefault(str(fy), {})[lea] = dict(gen=gen, grants=gr, total=tot, pp=pp, row=i)
        elif code in EDGE and r[7] == 'In-District':
            edge.setdefault(str(fy), {}).setdefault(lea, {})[code] = dict(total=r[10], pp=r[11])
        if lea in DETAIL:
            detail.setdefault(str(fy), {}).setdefault(lea, []).append(
                dict(row=i, cat=r[3], cat_desc=r[4], code=code, desc=r[6], where=r[7],
                     gen=r[8] or 0, grants=r[9] or 0, total=r[10] or 0, pp=r[11]))
    if bad:
        fail('%d TTPP rows do not foot: %s' % (len(bad), '; '.join(bad[:5])))
    return dict(version=VERSION, rows=rows, census=census, ttpp=ttpp, edge=edge, names=names,
                detail=detail)


def raw():
    if not os.path.exists(PATH):
        fail('%s is not here; run sync_archive.py --pull.' % KEY)
    sha = _sha()
    cp = os.path.join(CACHE, 'dese-functions-%s.json' % sha[:16])
    if os.path.exists(cp):
        d = json.load(open(cp, encoding='utf-8'))
        if d.get('version') == VERSION and d.get('sha256') == sha:
            return d
    d = _read()
    d['sha256'] = sha
    os.makedirs(CACHE, exist_ok=True)
    tmp = cp + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(d, fh)
    os.replace(tmp, cp)
    return d


def measures():
    """Everything the two shelves draw, derived from raw() and asserted."""
    d = raw()
    capital = {k: v for k, v in d['census'].items() if k in '678'}
    if capital:
        fail('%s now carries function codes starting %s (%d rows); the pages say it carries '
             'no capital, debt or community-services rows' % (KEY, sorted(capital), sum(capital.values())))
    years = sorted(int(y) for y in d['ttpp'])
    sw = {int(r['fy']): r for r in csv.DictReader(open(STATEWIDE, encoding='utf-8'))
          if r['level'] == 'total' and r['func_code'] == 'TTPP'}
    if sorted(sw) != years:
        fail('dese-function-statewide.csv covers %s, the workbook %s' % (sorted(sw), years))
    voc = sorted(l for l in d['names'] if l.startswith('08'))
    if MONTY not in voc:
        fail('Monty Tech (LEA %s) is not among the 08 regional vocational codes' % MONTY)
    by_year = []
    for y in years:
        t = d['ttpp'][str(y)]
        vpp = {l: t[l]['pp'] for l in voc if l in t and t[l]['pp']}
        if MONTY not in vpp or LUNENBURG not in t or not (t.get(HARVARD) or {}).get('pp'):
            fail('FY%d: no TTPP row for Monty Tech, Lunenburg or Harvard' % y)
        rank = 1 + sum(1 for v in vpp.values() if v > vpp[MONTY])
        # Among every district DESE prints a figure for, highest first (a $0 district, which
        # has no pupils of its own, is not ranked).
        app = [r['pp'] for r in t.values() if r['pp']]
        s = sw[y]
        if float(s['lunenburg_per_pupil']) != t[LUNENBURG]['pp']:
            fail('FY%d: the statewide extract says Lunenburg %s, the workbook %s'
                 % (y, s['lunenburg_per_pupil'], t[LUNENBURG]['pp']))
        if int(s['districts']) != len(t):
            fail('FY%d: the statewide extract counts %s districts, the workbook has %d TTPP rows'
                 % (y, s['districts'], len(t)))
        by_year.append(dict(
            fy=y, districts=int(s['districts']), state_median=float(s['per_pupil_median']),
            vocational=len(vpp), vocational_median=statistics.median(vpp.values()),
            monty=t[MONTY]['pp'], monty_rank=rank, monty_total=t[MONTY]['total'],
            monty_gen=t[MONTY]['gen'], monty_grants=t[MONTY]['grants'],
            lunenburg=t[LUNENBURG]['pp'], lunenburg_total=t[LUNENBURG]['total'],
            lunenburg_gen=t[LUNENBURG]['gen'], lunenburg_grants=t[LUNENBURG]['grants'],
            harvard=t[HARVARD]['pp'], harvard_total=t[HARVARD]['total'],
            ranked=len(app), harvard_rank=1 + sum(1 for v in app if v > t[HARVARD]['pp']),
            lunenburg_rank=1 + sum(1 for v in app if v > t[LUNENBURG]['pp'])))
    last = years[-1]
    e = d['edge'][str(last)]
    eq = {l: e[l]['2420']['pp'] for l in voc if l in e and '2420' in e[l]}
    return dict(
        key=KEY, sha256=d['sha256'], rows=d['rows'],
        districts=len(d['names']), first_fy=years[0], last_fy=last,
        census={k: d['census'][k] for k in sorted(d['census'])},
        codes_counted=sorted(k for k in d['census'] if k.isdigit()),
        by_year=by_year,
        vocational_names={l: d['names'][l] for l in voc},
        equipment=dict(fy=last, by_district={d['names'][l]: v for l, v in eq.items()},
                       monty=eq.get(MONTY), median=statistics.median(eq.values()),
                       districts=len(eq)),
        edge_last={'monty': e.get(MONTY, {}), 'lunenburg': e.get(LUNENBURG, {})},
        edge_by_year={y: {'monty': d['edge'][str(y)].get(MONTY, {}),
                          'lunenburg': d['edge'][str(y)].get(LUNENBURG, {})} for y in years},
        federal=census())


# ------------------------------------------------------------------ one district, line by line
# DESE's per-pupil total split into the categories it is built from. The file's own structure,
# asserted rather than assumed: each category's rollup row is the sum of its function rows; the
# ten in-district categories sum to IIII; tuition (TUIT) plus out-of-district transportation
# (ODTR) is OODD; IIII plus OODD is TTPP. A file that stops footing refuses the page.
IN_CATS = ('ADMN', 'LDRS', 'TCHR', 'TSER', 'PDEV', 'MATL', 'GUID', 'SERV', 'OPMN', 'BENE')
OUT_CATS = ('TUIT', 'ODTR')
# Short names for a chart row; the table carries DESE's own names beside them.
CAT_SHORT = {'ADMN': 'Administration', 'LDRS': 'Instructional leadership', 'TCHR': 'Teachers',
             'TSER': 'Other teaching services', 'PDEV': 'Professional development',
             'MATL': 'Materials, equipment, technology',
             'GUID': 'Guidance, counselling, testing',
             'SERV': 'Pupil services: buses, meals, sport',
             'OPMN': 'Operations and maintenance', 'BENE': 'Insurance, retirement, other',
             'TUIT': 'Tuition to other schools', 'ODTR': 'Out-of-district transportation'}
# THE DENOMINATOR (build_peer_spending.py, docstring point 3): DESE's TTPP figure is over TOTAL
# FTE pupils and every category's printed figure over IN-DISTRICT FTE pupils, so the printed
# category figures do not add to the printed total. breakdown() divides every category by
# TOTAL FTE pupils -- our division, which is what makes the parts add to DESE's total. Both
# counts are DESE's own, from RADAR (sources/data/dese-radar.csv).
RADAR = os.path.join(ROOT, 'sources', 'data', 'dese-radar.csv')
TOL = 2   # dollars: DESE prints whole dollars, so a rollup may differ from its parts by rounding


def fte(lea, fy):
    got = {r['measure']: float(r['value']) for r in csv.DictReader(open(RADAR, encoding='utf-8'))
           if r['lea'] == lea and r['fy'] == str(fy)
           and r['measure'] in ('Total FTE Pupils', 'In-District FTE Pupils')}
    if len(got) != 2:
        fail('dese-radar.csv has no FTE pupil counts for %s FY%s' % (lea, fy))
    return got['Total FTE Pupils'], got['In-District FTE Pupils']


def breakdown(lea, fy):
    """One district's DESE per-pupil total, category by category, footed to DESE's own TTPP row.
    Every category: general fund, grants and revolving funds, all funds, a pupil (over TOTAL FTE
    pupils), and its share of the total. `lines` are the function rows, for the table."""
    d = raw()
    if lea not in DETAIL:
        fail('breakdown(%s): only %s are extracted line by line' % (lea, DETAIL))
    rows = d['detail'].get(str(fy), {}).get(lea)
    if not rows:
        fail('no FY%s rows for %s' % (fy, lea))
    roll = {r['code']: r for r in rows if r['code'] == r['cat']}
    lines = [r for r in rows if r['code'] != r['cat']]
    known = set(IN_CATS) | {'IIII', 'OODD', 'ODTR', 'TTPP'}
    if set(roll) - known or not {'IIII', 'OODD', 'TTPP'} <= set(roll):
        fail('FY%s %s: rollup rows are %s, not the categories this split knows'
             % (fy, lea, sorted(roll)))
    if {r['cat'] for r in lines} - set(IN_CATS) - {'TUIT'}:
        fail('FY%s %s: function rows under an unknown category %s'
             % (fy, lea, sorted({r['cat'] for r in lines} - set(IN_CATS) - {'TUIT'})))
    zero = dict(gen=0, grants=0, total=0)
    K = ('gen', 'grants', 'total')

    def foot(name, want, parts):
        for k in K:
            got = sum(p[k] for p in parts)
            if abs(got - want[k]) > TOL:
                fail('FY%s %s: %s %s is %s, its parts sum to %s' % (fy, lea, name, k, want[k], got))

    cats = []
    for c in IN_CATS:
        mine = [r for r in lines if r['cat'] == c]
        r = roll.get(c)
        if r is None:
            if mine:
                fail('FY%s %s: %s has function rows and no rollup' % (fy, lea, c))
            continue
        foot(c, r, mine)
        cats.append(dict(code=c, desc=r['cat_desc'], dese_pp=r['pp'], **{k: r[k] for k in K}))
    foot('IIII (in-district)', roll['IIII'], cats)
    tuit = [r for r in lines if r['cat'] == 'TUIT']
    if tuit:
        cats.append(dict(code='TUIT', desc=tuit[0]['cat_desc'], dese_pp=None,
                         **{k: sum(r[k] for r in tuit) for k in K}))
    if 'ODTR' in roll and roll['ODTR']['total']:
        cats.append(dict(code='ODTR', desc=roll['ODTR']['cat_desc'], dese_pp=None,
                         **{k: roll['ODTR'][k] for k in K}))
    foot('OODD (out-of-district)', roll['OODD'], [c for c in cats if c['code'] in OUT_CATS] or [zero])
    t = roll['TTPP']
    foot('TTPP (the per-pupil total)', t, cats)
    ft, fi = fte(lea, fy)
    if abs(t['total'] / ft - t['pp']) > 1:
        fail('FY%s %s: DESE prints %s a pupil; its total over %s total FTE pupils is %.2f'
             % (fy, lea, t['pp'], ft, t['total'] / ft))
    for c in cats:
        if c['code'] in IN_CATS and abs(c['total'] / fi - c['dese_pp']) > 1:
            fail('FY%s %s: %s prints %s a pupil, not its total over %s in-district FTE pupils'
                 % (fy, lea, c['code'], c['dese_pp'], fi))
        c.update(short=CAT_SHORT[c['code']], pp=c['total'] / ft, gen_pp=c['gen'] / ft,
                 grants_pp=c['grants'] / ft, share=100.0 * c['total'] / t['total'])
    return dict(lea=lea, name=d['names'][lea], fy=fy, fte_total=ft, fte_in=fi,
                gen=t['gen'], grants=t['grants'], total=t['total'], pp=t['pp'],
                cats=cats, lines=lines, rows_in_file=d['rows'],
                capital_rows=sum(v for k, v in d['census'].items() if k in '678'))


# The function rows the line-by-line table shows beside the categories: the ones a reader asks
# about -- classroom teachers, aides, equipment, buses, meals, sport, pensions and insurance.
LINES = ('2305', '2330', '2420', '3300', '3400', '3510', '5100', '5200', '5250')


def breakdown_chart(b):
    """THE ONE FORMAT both line-by-line pages draw: each category a pupil, split by who paid."""
    import topic as TP
    import conclusions as C
    return TP.ranking(
        'A pupil, by what it paid for',
        [(c['short'], [c['gen_pp'], c['grants_pp']]) for c in b['cats']], '$',
        stack=['General fund', 'Grants and revolving funds'],
        note='DESE, all funds, %s. Each category over all %s FTE pupils, our division, so the '
             'rows add to DESE’s %s.' % (C.fy(b['fy']), '{:,.1f}'.format(b['fte_total']),
                                        C.usd(b['pp'])),
        note_figures={'y': C.figure(b['fy'], C.fy(b['fy']), 'fiscal year'),
                      'n': C.figure(b['fte_total'], '{:,.1f}'.format(b['fte_total']), 'FTE pupils'),
                      'a': C.figure(b['pp'], C.usd(b['pp']))})


def breakdown_table(b):
    import conclusions as C
    cols = ['A pupil', 'All funds', 'General fund', 'Grants, revolving', 'Share']
    cat_rows = [dict(label=c['desc'], cells=[C.usd(c['pp']), C.usd(c['total']), C.usd(c['gen']),
                                             C.usd(c['grants']), C.pct(c['share'], 1)])
                for c in b['cats']]
    cat_rows.append(dict(label='Total, as DESE prints it', cells=[
        C.usd(b['pp']), C.usd(b['total']), C.usd(b['gen']), C.usd(b['grants']), C.pct(100, 0)]))
    by = {r['code']: r for r in b['lines'] if r['where'] == 'In-District'}
    line_rows = [dict(label='%s (%s)' % (by[k]['desc'], k), cells=[
        C.usd(by[k]['total'] / b['fte_total']), C.usd(by[k]['total']), C.usd(by[k]['gen']),
        C.usd(by[k]['grants'])]) for k in LINES if k in by]
    return dict(caption='%s, %s, line by line' % (SHORT_NAME[b['lea']], C.fy(b['fy'])), views=[
        dict(key='categories', label='DESE’s categories', columns=cols, kinds=['ledger'] * 5,
             total_col=0, rows=cat_rows,
             note='DESE’s expenditures by function, all funds, after the year closed. A pupil: '
                  'our division by total FTE pupils, so the rows add to the total. DESE prints '
                  'each category over in-district pupils, a different figure.'),
        dict(key='lines', label='Lines inside them', columns=cols[:4], kinds=['ledger'] * 4,
             total_col=0, rows=line_rows,
             note='Single function rows from the same file, by DESE function code. A pupil: '
                  'over total FTE pupils, as above.')])


SHORT_NAME = {LUNENBURG: 'Lunenburg', MONTY: 'Monty Tech', HARVARD: 'Harvard'}


def census():
    """The two districts in the Census Bureau's FY2024 table, in DOLLARS (the file's thousands
    times 1,000), with both identities the documentation states asserted for every
    Massachusetts row: TOTALEXP = TCURELSC + NONELSEC + TCAPOUT + L12 + M12 + Q11 + I86, and
    TCAPOUT = F12 + G15 + K09 + K10 + K11 + J99."""
    if not os.path.exists(CENSUS_PATH):
        fail('%s is not here; run sync_archive.py --pull.' % CENSUS_KEY)
    sha = _sha(CENSUS_PATH)
    cp = os.path.join(CACHE, 'census-elsec-%s.json' % sha[:16])
    if os.path.exists(cp):
        rows = json.load(open(cp, encoding='utf-8'))
    else:
        import openpyxl
        ws = openpyxl.load_workbook(CENSUS_PATH, read_only=True).worksheets[0]
        rows, head = {}, None
        for r in ws.iter_rows(values_only=True):
            if head is None:
                head = list(r)
                miss = [f for f in ('FIPST', 'NCESID', 'YRDATA') + CENSUS_FIELDS if f not in head]
                if miss:
                    fail('%s: no column %s' % (CENSUS_KEY, miss))
                continue
            x = dict(zip(head, r))
            if x['FIPST'] == '25':
                rows[x['NCESID']] = {f: x[f] for f in ('YRDATA',) + CENSUS_FIELDS}
        os.makedirs(CACHE, exist_ok=True)
        with open(cp + '.tmp', 'w', encoding='utf-8') as fh:
            json.dump(rows, fh)
        os.replace(cp + '.tmp', cp)
    bad = []
    for nid, x in rows.items():
        if x['TOTALEXP'] != sum(x[k] for k in ('TCURELSC', 'NONELSEC', 'TCAPOUT', 'L12', 'M12',
                                               'Q11', 'I86')):
            bad.append('%s TOTALEXP' % nid)
        if x['TCAPOUT'] != sum(x[k] for k in ('F12', 'G15', 'K09', 'K10', 'K11', 'J99')):
            bad.append('%s TCAPOUT' % nid)
    if bad:
        fail('%s: %d Massachusetts rows break an identity the documentation states: %s'
             % (CENSUS_KEY, len(bad), bad[:5]))
    out = {}
    for nid, lea in CENSUS_IDS.items():
        x = rows.get(nid)
        if x is None or str(x['YRDATA']) != str(CENSUS_FY)[2:]:
            fail('%s: no FY%d row for NCES id %s' % (CENSUS_KEY, CENSUS_FY, nid))
        out[lea] = dict({k: (v * 1000 if k not in ('NAME', 'UNIT_TYPE', 'V33', 'YRDATA') else v)
                         for k, v in x.items()}, nces=nid)
    return dict(fy=CENSUS_FY, key=CENSUS_KEY, systems=len(rows), by_lea=out)


if __name__ == '__main__':
    m = measures()
    by = m.pop('by_year')
    json.dump(m, sys.stdout, indent=1, default=str)
    print()
    for r in by:
        print(r)
