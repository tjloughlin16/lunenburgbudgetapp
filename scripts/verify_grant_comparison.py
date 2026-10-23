#!/usr/bin/env python3
"""Every headline figure on the two grant-comparison pages, recomputed by a different route.

    python3 scripts/verify_grant_comparison.py

The generator (build_grant_comparison_topics.py) builds the comparison sets by CALLING
build_town_comparison.cohort() and joins through its own lookups. This reads the cohorts off the
PUBLISHED towns-like-us.json payload instead (role `structural` / `behavioural`), reads the raw
CSV and the DESE profile itself with no shared helper, computes its own medians and its own
correlation, and compares each to the value the page prints. A figure that disagrees fails.
"""
import csv
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_town_comparison import NEIGHBOURS, PEERS, DISTRICT_OF  # noqa: E402  (definitions only)

TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
YEAR = 2025


def facts(tid):
    d = json.load(open(os.path.join(TOPICS, tid + '.json'), encoding='utf-8'))
    return {f['id']: f['value']['value'] for f in d['facts']}


# ---------------------------------------------------------------- the presence matrix, page two
# A DIFFERENT ROUTE from extract_dese_awards.py + the generator: the award documents are read
# again here with xml.etree (not regex), and a district is "on" a document when its name
# appears AS WORDS anywhere in a recipient's printed text -- looser than the extractor's exact
# normalised match plus its reviewed list. The two routes must give the same dots; where the
# loose route over-reaches, the only exceptions are these, each a recipient that names a
# district without being it, read on 23 October 2026:
NOT_THE_DISTRICT = ('nashoba learning group', 'nashoba valley', 'hilltown coop')
AWARD_DIR = os.path.join(ROOT, 'sources', 'state-dese', 'awards')
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def read_award(path):
    import re
    import zipfile
    import xml.etree.ElementTree as ET
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    text = lambda el: ' '.join(''.join(t.text or '' for t in el.iter(W + 't')).split())
    recips = []
    for tbl in root.iter(W + 'tbl'):
        trs = [[text(tc) for tc in tr.findall(W + 'tc')] for tr in tbl.findall(W + 'tr')]
        if trs and len(trs[0]) >= 2 and 'recipient' in trs[0][0].lower():
            for tr in trs[1:]:
                m = re.search(r'([\d,]+(?:\.\d\d)?)', tr[-1].replace(' ', ''))
                if tr[0] and m and re.search(r'\d', m.group(1)):
                    recips.append((tr[0], float(m.group(1).replace(',', ''))))
    body = ' '.join(text(p) for p in root.iter(W + 'p'))
    got = lambda k: int(re.search(k + r':?\s*(\d+)', body).group(1))
    return recips, got('Proposals Received'), got('Proposals Recommended')


def words(s):
    import re
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s.lower().replace('\u2019', "'")) + ' '


def competitive(code, comp, lun, names):
    import re
    d = json.load(open(os.path.join(TOPICS, 'grants-others-receive.json'), encoding='utf-8'))
    ch = d['chart']
    want_names = {c: n for n, c in code.items() if c in set(comp) | {lun}}
    # the column a district is drawn in, by its label (the page strips " School District")
    col = {i: lab for i, lab in enumerate(ch['columns'])}
    by_label = {}
    for c, n in want_names.items():
        by_label[n.replace(' School District', '')] = c
    # Monty Tech: drawn beside Lunenburg, in no count. Its code is read off the allocation CSV
    # by DESE's own label, here as in the generator, but by a separate read.
    mts = {r['district_code'] for r in csv.DictReader(open(os.path.join(
        ROOT, 'sources', 'data', 'dese-entitlement-allocations.csv'), encoding='utf-8'))
        if r['district'] == 'Montachusett Regional Vocational Technical'}
    if len(mts) != 1:
        return ['Monty Tech does not resolve to one code: %s' % sorted(mts)], {}
    mt = mts.pop()
    by_label['Monty Tech'] = mt
    if ch.get('related') != [ch['columns'].index('Monty Tech')]:
        return ['Monty Tech is not the one related (uncounted) column'], {}
    counted = set(comp)
    if set(by_label) != set(col.values()):
        return ['presence columns %s are not the comparison districts and Lunenburg'
                % sorted(set(col.values()) ^ set(by_label))], {}
    # every award document held, read again
    docs = {}
    for fy in sorted(os.listdir(AWARD_DIR)):
        if not re.fullmatch(r'fy\d{4}', fy):
            continue
        for f in sorted(os.listdir(os.path.join(AWARD_DIR, fy))):
            if f.endswith('.docx'):
                docs[(int(fy[2:]), f[:-5].upper())] = read_award(os.path.join(AWARD_DIR, fy, f))
    won = {}
    for (fy, fc), (recips, _, _) in docs.items():
        for text_, amt in recips:
            w = words(text_)
            if any(x in w.strip() for x in NOT_THE_DISTRICT):
                continue
            for lab, c in list(by_label.items()) + [('Montachusett', mt)]:
                if words(lab.replace('-', ' ')) in w or words(lab) in w:
                    won.setdefault(fc, {}).setdefault(c, []).append((fy, amt))
    bad = []
    comp_rows = ch['groups'][0]['rows']
    short_of = {}
    for r in ch['groups'][0]['rows'] + ch['groups'][1]['rows']:
        n = sum(1 for i, v in enumerate(r['cells']) if v and by_label[col[i]] in counted)
        if r['count'] != n:
            bad.append('presence row %r counts %d, recomputed %d without Monty Tech or Lunenburg'
                       % (r['label'], r['count'], n))
    for r in comp_rows:
        on = {by_label[col[i]] for i, v in enumerate(r['cells']) if v}
        hit = [fc for fc in won if set(won[fc]) == on]
        if not hit:
            bad.append('presence row %r: page dots %s match no award document read again'
                       % (r['label'], sorted(want_names[c] for c in on)))
            continue
        short_of[r['label']] = hit
    # every grant a district won is a row: none dropped
    if len([fc for fc in won]) != len(comp_rows):
        bad.append('the award documents give %d grants with a comparison or Lunenburg winner; '
                   'the page draws %d rows' % (len(won), len(comp_rows)))
    # formula rows, straight off the allocation CSV
    alloc = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] and r['amount'] not in ('', '0') and 2023 <= int(r['fy']) <= 2027:
            alloc.setdefault(r['fund_code'], set()).add(r['district_code'])
    f_rows = ch['groups'][1]['rows']
    want_f = {fc: s & (set(comp) | {lun, mt}) for fc, s in alloc.items() if s & (set(comp) | {lun})}
    page_f = [{by_label[col[i]] for i, v in enumerate(r['cells']) if v} for r in f_rows]
    if sorted(map(sorted, want_f.values())) != sorted(map(sorted, page_f)):
        bad.append('the formula rows do not match the allocation CSV, FY2023-FY2027')
    # Monty Tech's Perkins line, in a conclusion note: years allocated and the FY2025 amount
    perk = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == mt and r['fund_code'] == '0400' and r['amount'] not in ('', '0'):
            perk[int(r['fy'])] = int(r['amount'])
    yrs = [y for y in range(2023, 2028) if y in perk]
    line = '%d of 5 years, $%s in FY2025' % (len(yrs), format(perk[2025], ','))
    notes = [n['text'] for c in d['conclusions'] for n in c.get('notes', [])]
    if not any(line in t for t in notes):
        bad.append('Monty Tech Perkins note: expected %r on the page' % line)
    # the facts
    gap = [fc for fc, ws in won.items() if lun not in ws]
    per = {c: sum(1 for ws in won.values() if c in ws) for c in comp}
    opps = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-grant-opportunities.csv'), encoding='utf-8')):
        for fc in re.split(r'[^0-9A-Za-z]+', r['fund_code']):
            if fc:
                opps[fc.upper()] = r
    openc = [fc for fc in gap if fc in opps and opps[fc]['grant_type'] == 'Competitive'
             and opps[fc]['district_reading'] == 'districts eligible']
    ebp = [(fy, fc) for fc, ws in won.items() if lun in ws and not (set(ws) - {lun})]
    if len(ebp) != 1:
        bad.append('expected one grant Lunenburg alone won, found %d' % len(ebp))
        return bad, {}
    fc_e = ebp[0][1]
    (fy_e, amt_e), = won[fc_e][lun]
    _, rcv, rec = docs[(fy_e, fc_e)]
    t3 = sum(1 for c in comp if c in alloc.get('0180', set()))
    return bad, {'c-gap': len(gap), 'c-who': sum(1 for c in comp if per[c]),
                 'c-top': max(per.values()), 'c-lun': sum(1 for ws in won.values() if lun in ws),
                 'c-open': len(openc),
                 'c-still': sum(1 for fc in openc if opps[fc]['open_on_list_date'] == 'yes'),
                 'ebp': amt_e, 'ebp-n': rec, 't3-ever': t3}


def main():
    twins = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'towns-like-us.json'),
                           encoding='utf-8'))['twins']
    makeup = [t['district'] for t in twins if t['role'] == 'structural']
    behaviour = [t['district'] for t in twins if t['role'] == 'behavioural']
    names = set(DISTRICT_OF[t] for t in NEIGHBOURS + PEERS) | set(makeup) | set(behaviour)
    names.discard('Fitchburg')            # DESE's two `Fitchburg` codes; the page leaves it out

    prof = {}
    code = {}
    for r in json.load(open(os.path.join(ROOT, 'sources', 'state-dese', 'er3w-dyti.json'),
                            encoding='utf-8')):
        if r['sy'] != str(YEAR) or r['ind_value'] in (None, ''):
            continue
        code[r['dist_name']] = r['dist_code'][:4]
        prof.setdefault(r['dist_code'][:4], {})[r['ind_subcat']] = float(r['ind_value'])
    amt = {}
    pages = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['fy'] != str(YEAR) or not r['district_code'] or r['amount'] == '':
            continue
        amt[(r['district_code'], r['fund_code'])] = float(r['amount'])
    lun = code['Lunenburg']
    comp = sorted(code[n] for n in names)
    hc = lambda c: prof[c]['Student Headcount']
    pp = lambda c, fc: amt[(c, fc)] / hc(c)
    five = ['0305', '0140', '0309', '0240', '0262']

    got1, got2 = facts('grant-allocations-compared'), facts('grants-others-receive')
    mk = [code[n] for n in makeup]
    want1 = {
        'idea-l': round(pp(lun, '0240')),
        'idea-med': round(st.median(pp(c, '0240') for c in comp)),
        'idea-below': sum(pp(c, '0240') < pp(lun, '0240') for c in comp),
        'ti-l': round(pp(lun, '0305')),
        'ti-mk': round(st.median(pp(c, '0305') for c in mk)),
        'li-l': prof[lun]['Low-Income % Headcount'],
        'li-mk': st.median(prof[c]['Low-Income % Headcount'] for c in mk),
        'five-l': round(sum(pp(lun, fc) for fc in five)),
        'five-med': round(st.median(sum(pp(c, fc) for fc in five) for c in comp)),
    }
    xs, ys = [], []
    for c, p in prof.items():
        if (c, '0305') in amt and 'Student Headcount' in p and 'Low-Income % Headcount' in p:
            xs.append(p['Low-Income % Headcount'])
            ys.append(amt[(c, '0305')] / p['Student Headcount'])
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    r = (sum((a - mx) * (b - my) for a, b in zip(xs, ys))
         / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)))
    want1['r-ti'] = round(r, 2)
    t3 = [c for c in comp if amt.get((c, '0180'), 0) > 0]
    rates = [amt[(c, '0180')] / (p['Student Headcount'] * p['English learner % Headcount'] / 100)
             for c, p in prof.items()
             if amt.get((c, '0180')) and p.get('Student Headcount') and p.get('English learner % Headcount')]
    learners = hc(lun) * prof[lun]['English learner % Headcount'] / 100
    want2 = {'est': round(learners * st.median(rates))}
    bad2, w2 = competitive(code, comp, lun, names)
    want2.update(w2)
    bad = list(bad2)
    if len(comp) != 28:
        bad.append('expected 28 comparison districts, found %d' % len(comp))
    if any(k[0] == lun and k[1] == '0180' for k in amt):
        bad.append('Lunenburg has a Title III row')
    for got, want, tid in ((got1, want1, 'grant-allocations-compared'),
                           (got2, want2, 'grants-others-receive')):
        for k, v in want.items():
            g = got.get(k)
            if g is None or abs(float(g) - float(v)) > 1e-6:
                bad.append('%s %s: page %r, recomputed %r' % (tid, k, g, v))
    if bad:
        print('\n'.join(bad))
        return 1
    print('grant comparison: %d figures and every dot of the presence matrix recomputed, all agree'
          % (len(want1) + len(want2)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
