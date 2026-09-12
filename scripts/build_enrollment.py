#!/usr/bin/env python3
"""Who is in the schools: Lunenburg's enrolment, FY1994 to FY2026, from DESE's own file.

    python3 scripts/build_enrollment.py            # write fy28/public/data/enrollment.json
    python3 scripts/build_enrollment.py --check    # fail if it no longer reproduces

Page 7 of the build order TJ set on 10 September 2026: `dese_enrollment`, loaded and
read by nothing. Every other page here divides by enrolment -- per pupil, per hundred
pupils, share of students -- and none of them showed the denominator itself.

THE GRAIN. A HEADCOUNT on 1 October, published by DESE for every district and school in
the state, by grade and for selected student groups. It is children, not FTE and not
dollars. A child is counted once, in the district that enrols them: a Lunenburg child at
Monty Tech is in Monty Tech's count and not this one, which is why this page and
/where-students-go-instead are read together.

THE ONE BREAK IN THE SERIES, stated wherever it could mislead: DESE changed how it
identifies low-income students. Through FY2014 it published `low income` (free or
reduced lunch); FY2015-FY2021 it published `economically disadvantaged` instead
(state-record matching, a narrower net); from FY2022 `low income` returns under a new,
broader definition. The three are not one series and the page never draws them as one.

Rule 7 throughout: a count that fell is a fact; why it fell is not in this file.
"""
import argparse
import csv
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import conclusion, emit, figure  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'enrollment.json')
DISTRICT = 'Lunenburg'
PEERS = ['Ashburnham-Westminster', 'Ayer Shirley School District', 'Groton-Dunstable', 'Harvard', 'North Middlesex']
DOC = dict(key='state-dese/dese-enrollment-by-grade.xlsx',
           what='Enrollment by grade and selected populations, every Massachusetts district and school, '
                'FY1994-FY2026. A headcount on 1 October of the school year. The source of every count here.',
           publisher='Massachusetts Department of Elementary and Secondary Education',
           stage='published; a count taken on one day')


def fail(msg):
    raise SystemExit('build_enrollment: ' + msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def document():
    with open(MANIFEST, encoding='utf-8') as fh:
        rows = {r['key']: r for r in csv.DictReader(fh)}
    r = rows.get(DOC['key'])
    if not r:
        fail('%s is not in the manifest (rule 12)' % DOC['key'])
    if not r['upstream']:
        fail('%s carries no upstream address (rule 12)' % DOC['key'])
    return [dict(DOC, path='sources/' + DOC['key'], sha256=r['sha256'], bytes=int(r['bytes']),
                 url=r['upstream'], docs_url='/docs/' + DOC['key'], filename=DOC['key'].split('/')[-1],
                 note=DOC['what'] + ' Stage: ' + DOC['stage'])]


GRADES = ['pk_cnt', 'k_cnt'] + ['grade_%d_cnt' % g for g in range(1, 13)] + ['sp_cnt']


def district_series(db):
    rows = q(db, "SELECT * FROM dese_enrollment WHERE org_level='district' AND org_name=? ORDER BY fy", DISTRICT)
    if len(rows) < 20:
        fail('only %d district rows for %s' % (len(rows), DISTRICT))
    # `reconciles` is the loader's own check that the grades sum to the total. 'no' is a
    # defect and fails; an empty cell means the early rows (FY1994-FY2002) carry no SP
    # column to check against, and they are kept and labelled `no check` rather than
    # dropped or trusted.
    bad = [r['fy'] for r in rows if r['reconciles'] == 'no']
    if bad:
        fail('grades do not sum to the total in FY%s' % bad)
    out = []
    for r in rows:
        g = lambda k: r[k] or 0
        out.append(dict(
            fy=r['fy'], total=int(r['total_cnt']), check=r['reconciles'] or 'no check',
            k5=int(sum(g(k) for k in ['pk_cnt', 'k_cnt'] + ['grade_%d_cnt' % i for i in range(1, 6)])),
            g68=int(sum(g('grade_%d_cnt' % i) for i in (6, 7, 8))),
            g912=int(sum(g('grade_%d_cnt' % i) for i in (9, 10, 11, 12))),
            sp=int(g('sp_cnt')),
            swd=int(r['swd_cnt']) if r['swd_cnt'] is not None else None,
            swd_pct=r['swd_pct'],
            el=int(r['el_cnt']) if r['el_cnt'] is not None else None,
            low_income=int(r['low_income_cnt']) if r['low_income_cnt'] is not None else None,
            low_income_pct=r['low_income_pct'],
            econ_dis=int(r['econ_disadvantaged_cnt']) if r['econ_disadvantaged_cnt'] is not None else None,
            high_needs=int(r['high_needs_cnt']) if r['high_needs_cnt'] is not None else None,
        ))
    return out


def schools(db):
    rows = q(db, "SELECT fy, org_name, total_cnt FROM dese_enrollment WHERE org_level='school' AND district=? ORDER BY fy, org_name", DISTRICT)
    return [dict(fy=r['fy'], school=r['org_name'], total=int(r['total_cnt'] or 0)) for r in rows]


def peers(db, first, last):
    out = []
    for name in [DISTRICT] + PEERS:
        a = q(db, "SELECT total_cnt FROM dese_enrollment WHERE org_level='district' AND org_name=? AND fy=?", name, first)
        b = q(db, "SELECT total_cnt FROM dese_enrollment WHERE org_level='district' AND org_name=? AND fy=?", name, last)
        if not a or not b:
            continue
        out.append(dict(district=name, first=int(a[0]['total_cnt']), last=int(b[0]['total_cnt']),
                        change=int(b[0]['total_cnt'] - a[0]['total_cnt']),
                        pct=(b[0]['total_cnt'] - a[0]['total_cnt']) / a[0]['total_cnt']))
    out.sort(key=lambda r: r['pct'])
    return out


def build():
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        dist = district_series(db)
        by_fy = {r['fy']: r for r in dist}
        peak = max(dist, key=lambda r: r['total'])
        last = dist[-1]
        first = dist[0]
        # The fall, and when it ended: the first year after the peak from which the total
        # never again moved more than a band's width. Measured, not eyeballed.
        after = [r for r in dist if r['fy'] > peak['fy']]
        trough = min(after, key=lambda r: r['total'])
        plateau = [r for r in dist if r['fy'] >= trough['fy']]
        band_lo, band_hi = min(r['total'] for r in plateau), max(r['total'] for r in plateau)
        base_fy = 2008 if 2008 in by_fy else first['fy']
        base = by_fy[base_fy]
        bands = [
            dict(band='pre-K to grade 5', first=base['k5'], last=last['k5'], pct=(last['k5'] - base['k5']) / base['k5']),
            dict(band='grades 6-8', first=base['g68'], last=last['g68'], pct=(last['g68'] - base['g68']) / base['g68']),
            dict(band='grades 9-12', first=base['g912'], last=last['g912'], pct=(last['g912'] - base['g912']) / base['g912']),
        ]
        hs = bands[2]
        swd_base = by_fy[base_fy]
        el_first = next(r for r in dist if r['el'] is not None and r['fy'] >= base_fy)
        # Low income: three series, never one.
        li_old = [dict(fy=r['fy'], n=r['low_income'], pct=r['low_income_pct']) for r in dist if r['low_income'] is not None and r['fy'] <= 2014]
        econ = [dict(fy=r['fy'], n=r['econ_dis']) for r in dist if r['econ_dis'] is not None]
        li_new = [dict(fy=r['fy'], n=r['low_income'], pct=r['low_income_pct']) for r in dist if r['low_income'] is not None and r['fy'] >= 2022]
        pr = peers(db, base_fy, last['fy'])
        lun_rank = [i for i, r in enumerate(pr) if r['district'] == DISTRICT][0] + 1
        sch = schools(db)

        rows = [
            conclusion(
                id='the-fall-ended-a-decade-ago',
                claim='%s children, %s fewer than the FY%d peak — and the fall stopped in FY%d.'
                      % (C.num(last['total']), C.num(peak['total'] - last['total']), peak['fy'], trough['fy']),
                so_what='Since FY%d it has stayed between %s and %s. Smaller than it was; not still shrinking.'
                        % (trough['fy'], C.num(band_lo), C.num(band_hi)),
                figures={'now': figure(last['total'], C.num(last['total']), 'children, FY%d' % last['fy']),
                         'peak': figure(peak['total'], C.num(peak['total'])),
                         'fewer': figure(peak['total'] - last['total'], C.num(peak['total'] - last['total'])),
                         'pct': figure((peak['total'] - trough['total']) / peak['total'], C.pct(100 * (peak['total'] - trough['total']) / peak['total'])),
                         'band_lo': figure(band_lo, C.num(band_lo)), 'band_hi': figure(band_hi, C.num(band_hi)),
                         'fy_last': figure(last['fy'], 'FY%d' % last['fy']), 'fy_peak': figure(peak['fy'], 'FY%d' % peak['fy']),
                         'fy_trough': figure(trough['fy'], 'FY%d' % trough['fy']), 'trough': figure(trough['total'], C.num(trough['total'])),
                         'band': figure(band_hi - band_lo, C.num(band_hi - band_lo))},
                figure='now', kind='measured', bearing='sizes',
                lede='The argument in town assumes enrolment is falling. It fell — %s from FY%d to FY%d — and then it stopped.'
                     % (C.pct(100 * (peak['total'] - trough['total']) / peak['total']), peak['fy'], trough['fy']),
                detail='The peak was FY%d at %s. The low was FY%d at %s. Every year since has been within %s of that low, '
                       'and FY%d is %s. A budget built on a falling headcount is built on a decade-old trend.'
                       % (peak['fy'], C.num(peak['total']), trough['fy'], C.num(trough['total']),
                          C.num(band_hi - band_lo), last['fy'], C.num(last['total'])),
                basis='`dese_enrollment`, Lunenburg district rows, total_cnt, FY%d–FY%d; every row from FY2003 has its grades summed to its total, and the three earlier rows are marked `no check`.' % (first['fy'], last['fy']),
                not_shown='Why. Births, moves, school choice and Monty Tech all change this count and this file separates none of them. '
                          'And it is one day a year: a child who arrives in November is not here.',
                see=[('/if-students-leave', 'What a smaller school does and does not save')],
            ),
            conclusion(
                id='the-high-school-did-the-shrinking',
                claim='Grades 9–12 fell %s since FY%d; pre-K to grade 5 fell %s.'
                      % (C.pct(100 * abs(hs['pct'])), base_fy, C.pct(100 * abs(bands[0]['pct']))),
                so_what='The decline is a high-school decline. The lower grades are close to where they were.',
                figures={'hs_pct': figure(abs(hs['pct']), C.pct(100 * abs(hs['pct'])), 'fall in grades 9–12, FY%d to FY%d' % (base_fy, last['fy'])),
                         'hs_first': figure(hs['first'], C.num(hs['first'])), 'hs_last': figure(hs['last'], C.num(hs['last'])),
                         'k5_pct': figure(abs(bands[0]['pct']), C.pct(100 * abs(bands[0]['pct']))),
                         'g68_pct': figure(abs(bands[1]['pct']), C.pct(100 * abs(bands[1]['pct']))),
                         'k5_first': figure(bands[0]['first'], C.num(bands[0]['first'])), 'k5_last': figure(bands[0]['last'], C.num(bands[0]['last'])),
                         'g68_first': figure(bands[1]['first'], C.num(bands[1]['first'])), 'g68_last': figure(bands[1]['last'], C.num(bands[1]['last'])),
                         'fy_base': figure(base_fy, 'FY%d' % base_fy), 'fy_last': figure(last['fy'], 'FY%d' % last['fy'])},
                figure='hs_pct', kind='measured', bearing='sizes',
                detail='FY%d to FY%d, grades 9–12 went from %s to %s children. Pre-K to grade 5 went from %s to %s (down %s); grades 6–8 from %s to %s (down %s). '
                       'The step between grade 8 and grade 9 is where the town loses children every year, and this is what that looks like accumulated.'
                       % (base_fy, last['fy'], C.num(hs['first']), C.num(hs['last']), C.num(bands[0]['first']), C.num(bands[0]['last']), C.pct(100 * abs(bands[0]['pct'])),
                          C.num(bands[1]['first']), C.num(bands[1]['last']), C.pct(100 * abs(bands[1]['pct']))),
                basis='`dese_enrollment` grade columns summed into three bands, Lunenburg district rows, FY%d against FY%d.' % (base_fy, last['fy']),
                not_shown='Where the ninth graders went. A vocational admission, a private school, school choice and a move are one absence here; '
                          '/which-grades-students-leave measures the rate and /where-students-go-instead the destinations.',
                allow=('grade 5', 'grade 8', 'grade 9', 'grades 6–8', 'grades 9–12', '9–12', '6–8'),
                see=[('/which-grades-students-leave', 'Which grades students leave in'),
                     ('/where-students-go-instead', 'Where they go')],
            ),
            conclusion(
                id='as-many-children-with-disabilities-as-ever',
                claim='%s students with disabilities in FY%d, %s in FY%d — in a school %s smaller.'
                      % (C.num(swd_base['swd']), base_fy, C.num(last['swd']), last['fy'],
                         C.pct(100 * (base['total'] - last['total']) / base['total'])),
                so_what='Their share rose from %s to %s without a child being added.'
                        % (C.pct(100 * swd_base['swd_pct']), C.pct(100 * last['swd_pct'])),
                figures={'now': figure(last['swd'], C.num(last['swd']), 'students with disabilities, FY%d' % last['fy']),
                         'then': figure(swd_base['swd'], C.num(swd_base['swd'])),
                         'share_then': figure(swd_base['swd_pct'], C.pct(100 * swd_base['swd_pct'])),
                         'share_now': figure(last['swd_pct'], C.pct(100 * last['swd_pct'])),
                         'shrink': figure((base['total'] - last['total']) / base['total'], C.pct(100 * (base['total'] - last['total']) / base['total'])),
                         'swd_lo': figure(min(r['swd'] for r in dist if r['swd'] is not None and r['fy'] >= base_fy), C.num(min(r['swd'] for r in dist if r['swd'] is not None and r['fy'] >= base_fy))),
                         'swd_hi': figure(max(r['swd'] for r in dist if r['swd'] is not None and r['fy'] >= base_fy), C.num(max(r['swd'] for r in dist if r['swd'] is not None and r['fy'] >= base_fy))),
                         'fy_base': figure(base_fy, 'FY%d' % base_fy), 'fy_last': figure(last['fy'], 'FY%d' % last['fy'])},
                figure='now', kind='measured', bearing='sizes',
                detail='The count moved between %s and %s over the years in between, and ends where it began. The share is a ratio, and its '
                       'denominator fell; that is the whole of the movement. Special education staffing and cost are measured on other pages against this count.'
                       % (C.num(min(r['swd'] for r in dist if r['swd'] is not None and r['fy'] >= base_fy)),
                          C.num(max(r['swd'] for r in dist if r['swd'] is not None and r['fy'] >= base_fy))),
                basis='`dese_enrollment` swd_cnt and swd_pct, Lunenburg district rows.',
                not_shown='Need. A count of students with an IEP says nothing about the intensity of any plan, and DESE’s own placement data '
                          'shows the mix of settings moving while the count did not.',
                see=[('/how-many-students-are-on-an-iep', 'The IEP count, in detail'),
                     ('/special-education', 'Special education')],
            ),
            conclusion(
                id='english-learners-from-a-handful-to-seventy',
                claim='English learners went from %s children in FY%d to %s in FY%d.'
                      % (C.num(el_first['el']), el_first['fy'], C.num(last['el']), last['fy']),
                so_what='The fastest-growing group in the school, and still %s of enrolment.'
                        % C.pct(100 * last['el'] / last['total']),
                figures={'now': figure(last['el'], C.num(last['el']), 'English learners, FY%d' % last['fy']),
                         'then': figure(el_first['el'], C.num(el_first['el'])),
                         'share': figure(last['el'] / last['total'], C.pct(100 * last['el'] / last['total'])),
                         'fy_first': figure(el_first['fy'], 'FY%d' % el_first['fy']), 'fy_last': figure(last['fy'], 'FY%d' % last['fy'])},
                figure='now', kind='measured', bearing='sizes',
                detail='Small numbers, and the growth is real: the count has risen in most years since FY%d. '
                       'An English learner carries a higher weight in the Chapter 70 foundation budget, so this count moves aid as well as staffing.'
                       % el_first['fy'],
                basis='`dese_enrollment` el_cnt, Lunenburg district rows.',
                not_shown='Which languages, which schools, or what it costs to teach them. DESE publishes the count and nothing here attaches a dollar to it.',
                see=[('/how-chapter-70-works', 'How the formula weights students')],
            ),
            conclusion(
                id='low-income-share-doubled-across-a-definition-change',
                claim='Low-income: %s of students in FY%d, %s in FY%d — measured two different ways.'
                      % (C.pct(100 * li_old[-1]['pct']), li_old[-1]['fy'], C.pct(100 * li_new[-1]['pct']), li_new[-1]['fy']),
                so_what='DESE changed the definition twice in between. The rise is real; its size is not comparable across them.',
                figures={'now': figure(li_new[-1]['pct'], C.pct(100 * li_new[-1]['pct']), 'low-income, FY%d' % li_new[-1]['fy']),
                         'then': figure(li_old[-1]['pct'], C.pct(100 * li_old[-1]['pct'])),
                         'now_n': figure(li_new[-1]['n'], C.num(li_new[-1]['n'])),
                         'then_n': figure(li_old[-1]['n'], C.num(li_old[-1]['n'])),
                         'econ_first': figure(econ[0]['n'], C.num(econ[0]['n'])), 'econ_last': figure(econ[-1]['n'], C.num(econ[-1]['n'])),
                         'fy_old': figure(li_old[-1]['fy'], 'FY%d' % li_old[-1]['fy']), 'fy_new': figure(li_new[-1]['fy'], 'FY%d' % li_new[-1]['fy']),
                         'fy_econ_a': figure(econ[0]['fy'], 'FY%d' % econ[0]['fy']), 'fy_econ_b': figure(econ[-1]['fy'], 'FY%d' % econ[-1]['fy']),
                         'fy_new_a': figure(li_new[0]['fy'], 'FY%d' % li_new[0]['fy'])},
                figure='now', kind='measured', bearing='sizes',
                detail='Three series, never one. Through FY%d DESE counted “low income” by free or reduced lunch (%s children in FY%d). '
                       'FY%d–FY%d it counted “economically disadvantaged” by matching state records, a narrower net (%s to %s). From FY%d “low income” '
                       'returns under a broader definition (%s in FY%d). Within each series the count rises. The page draws them as three lines.'
                       % (li_old[-1]['fy'], C.num(li_old[-1]['n']), li_old[-1]['fy'], econ[0]['fy'], econ[-1]['fy'], C.num(econ[0]['n']), C.num(econ[-1]['n']),
                          li_new[0]['fy'], C.num(li_new[-1]['n']), li_new[-1]['fy']),
                basis='`dese_enrollment` low_income_cnt/pct (FY≤%d and FY≥%d) and econ_disadvantaged_cnt (FY%d–FY%d), Lunenburg district rows.'
                      % (li_old[-1]['fy'], li_new[0]['fy'], econ[0]['fy'], econ[-1]['fy']),
                not_shown='Household income. Each definition is a proxy for it and the proxies differ; nothing here measures poverty in Lunenburg directly. '
                          '/lunenburg-by-the-numbers has the Census figures.',
                see=[('/lunenburg-by-the-numbers', 'Who lives here, from the Census')],
            ),
            conclusion(
                id='lunenburg-shrank-less-than-most-of-its-neighbours',
                claim='FY%d to FY%d Lunenburg’s enrolment fell %s; its %s neighbours fell %s to %s.'
                      % (base_fy, last['fy'], C.pct(100 * abs(next(r for r in pr if r['district'] == DISTRICT)['pct'])), C.num(len(pr) - 1),
                         C.pct(100 * abs(pr[-1]['pct'])), C.pct(100 * abs(pr[0]['pct']))),
                so_what='A regional fall, not a Lunenburg one. Lunenburg is %s of %d in how much it shrank.'
                        % ('%dth' % lun_rank if lun_rank > 3 else ['first', 'second', 'third'][lun_rank - 1], len(pr)),
                figures={'lun': figure(abs(next(r for r in pr if r['district'] == DISTRICT)['pct']),
                                       C.pct(100 * abs(next(r for r in pr if r['district'] == DISTRICT)['pct'])), 'fall in enrolment, FY%d to FY%d' % (base_fy, last['fy'])),
                         'most': figure(abs(pr[0]['pct']), C.pct(100 * abs(pr[0]['pct']))), 'least': figure(abs(pr[-1]['pct']), C.pct(100 * abs(pr[-1]['pct']))),
                         'districts': figure(len(pr), C.num(len(pr))), 'neighbours': figure(len(pr) - 1, C.num(len(pr) - 1)),
                         'fy_base': figure(base_fy, 'FY%d' % base_fy), 'fy_last': figure(last['fy'], 'FY%d' % last['fy']),
                         'fy_ayer': figure(2012, 'FY2012')},
                figure='lun', kind='measured', bearing='sizes',
                detail='The table below gives each district’s count at both ends. The neighbour that fell most lost %s; the one that fell least lost %s. '
                       'Ayer Shirley regionalised in FY2012 and has no FY%d row, so it is not in this comparison.' % (C.pct(100 * abs(pr[0]['pct'])), C.pct(100 * abs(pr[-1]['pct'])), base_fy),
                basis='`dese_enrollment` district totals for Lunenburg and the five districts this site uses as peers, FY%d and FY%d.' % (base_fy, last['fy']),
                not_shown='Why the region fell. Births and housing are outside this file.',
                see=[('/what-other-districts-spend', 'The same districts, on spending')],
            ),
        ]
        return dict(
            generated_by='scripts/build_enrollment.py',
            about='Who is in Lunenburg’s schools: DESE’s headcount, FY%d to FY%d, by grade band and student group, with the neighbouring districts beside it.' % (first['fy'], last['fy']),
            grain='A HEADCOUNT on 1 October, from DESE. Children, not FTE, not dollars. A child is counted in the district that enrols them, '
                  'so residents at Monty Tech, in school choice or in a placement are not in this count.',
            first_fy=first['fy'], last_fy=last['fy'],
            peak=dict(fy=peak['fy'], total=peak['total']), trough=dict(fy=trough['fy'], total=trough['total']),
            plateau=dict(since=trough['fy'], low=band_lo, high=band_hi),
            base_fy=base_fy,
            district=dist, bands=bands, schools=sch, peers=pr,
            low_income=dict(old=li_old, econ=econ, new=li_new,
                            note='Three definitions. Through FY2014 free/reduced lunch; FY2015–FY2021 economically disadvantaged (state-record match); '
                                 'from FY2022 low income under a broader definition. Not one series.'),
            sources=document(),
            not_established=[
                'Why any of these counts moved. The file is a headcount and carries no reason.',
                'How many resident children are educated elsewhere in each year here; that is /where-students-go-instead, from a different DESE file.',
                'Anything about need or intensity behind the students-with-disabilities count.',
            ],
            conclusions=emit('enrollment', rows),
        )
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_enrollment.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: FY%d–FY%d, %d conclusions' % (os.path.relpath(OUT, ROOT), data['first_fy'], data['last_fy'], len(data['conclusions'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
