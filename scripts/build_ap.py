#!/usr/bin/env python3
"""Advanced Placement at Lunenburg High: who sits the exams, in what, and how they score,
SY2007 to SY2025, from DESE's two AP files.

    python3 scripts/build_ap.py            # write fy28/public/data/ap.json
    python3 scripts/build_ap.py --check    # fail if it no longer reproduces

Page 9 of the build order TJ set on 10 September 2026.

THE GRAIN, and it is three different things that must not be mixed:
    test_takers_cnt   CHILDREN who sat at least one AP exam that year
    tests_taken_cnt   SITTINGS -- one child sitting three exams is three
    score_1..score_5  TESTS at each score, not pupils; pct_3_5 is the share of tests
Subjects come as families ("History and Social Science") and as exams inside them; the
family rows are DESE's own rollups and are what this page sums, because the exam rows
carry the same exam under two names in some years and would double-count.

The one ratio this page makes is participation against the 11th and 12th grade
enrolment from `dese_enrollment`. It is an APPROXIMATION and labelled one: a tenth
grader can sit an AP exam, and the two files count on different days.

Rule 7: a rising pass rate is a measurement; whether the courses got better, the
students changed, or the district steered who sits is not in these files.
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
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'ap.json')
DISTRICT = 'Lunenburg'
DOCS = [
    dict(key='state-dese/dese-ap-participation.xlsx',
         what='AP participation, every Massachusetts district and school, SY2007-SY2025: children who sat at least one exam and sittings, by subject and student group.',
         publisher='Massachusetts Department of Elementary and Secondary Education', stage='published; counts'),
    dict(key='state-dese/dese-ap-performance.xlsx',
         what='AP performance, the same span: tests at each score 1-5 by subject and group. Small groups suppressed by DESE.',
         publisher='Massachusetts Department of Elementary and Secondary Education', stage='published; counts of tests'),
    dict(key='state-dese/dese-enrollment-by-grade.xlsx',
         what='Enrollment by grade; the grade 11 and 12 counts are the denominator for the participation ratio.',
         publisher='Massachusetts Department of Elementary and Secondary Education', stage='published; a count on one day'),
]


def fail(msg):
    raise SystemExit('build_ap: ' + msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def documents():
    with open(MANIFEST, encoding='utf-8') as fh:
        rows = {r['key']: r for r in csv.DictReader(fh)}
    out = []
    for d in DOCS:
        r = rows.get(d['key'])
        if not r or not r['upstream']:
            fail('%s is not in the manifest with an address (rule 12)' % d['key'])
        out.append(dict(d, path='sources/' + d['key'], sha256=r['sha256'], bytes=int(r['bytes']), url=r['upstream'],
                        docs_url='/docs/' + d['key'], filename=d['key'].split('/')[-1], note=d['what'] + ' Stage: ' + d['stage']))
    return out


def build():
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        part = q(db, "SELECT sy, test_takers_cnt takers, tests_taken_cnt sittings FROM dese_ap WHERE kind='participation' AND org_type='District' "
                     "AND org_name=? AND stu_grp='All Students' AND subj='All Subjects' ORDER BY sy", DISTRICT)
        perf = q(db, "SELECT sy, tests_taken, score_1, score_2, score_3, score_4, score_5, pct_3_5 FROM dese_ap WHERE kind='performance' AND org_type='District' "
                     "AND org_name=? AND stu_grp='All Students' AND subj='All Subjects' ORDER BY sy", DISTRICT)
        if len(part) < 10 or len(perf) < 10:
            fail('too few years: %d participation, %d performance' % (len(part), len(perf)))
        en = {r['fy']: r['g1112'] for r in q(db, "SELECT fy, grade_11_cnt+grade_12_cnt g1112 FROM dese_enrollment WHERE org_level='district' AND org_name=?", DISTRICT)}
        years = []
        for p in part:
            pf = next((x for x in perf if x['sy'] == p['sy']), None)
            if pf and pf['tests_taken'] and abs(pf['tests_taken'] - p['sittings']) > 0:
                fail('SY%d: %s sittings in participation, %s tests in performance' % (p['sy'], p['sittings'], pf['tests_taken']))
            years.append(dict(sy=p['sy'], takers=int(p['takers']), sittings=int(p['sittings']),
                              per_taker=p['sittings'] / p['takers'] if p['takers'] else None,
                              g1112=int(en[p['sy']]) if p['sy'] in en else None,
                              share_1112=(p['takers'] / en[p['sy']]) if p['sy'] in en and en[p['sy']] else None,
                              pass_share=pf['pct_3_5'] if pf else None,
                              scores=[int(pf['score_%d' % i] or 0) for i in range(1, 6)] if pf else None))
        first, last = years[0], years[-1]
        peak = max(years, key=lambda y: y['takers'])
        best = max((y for y in years if y['pass_share'] is not None), key=lambda y: y['pass_share'])
        worst = min((y for y in years if y['pass_share'] is not None), key=lambda y: y['pass_share'])
        # Subject families, DESE's own rollups (subj == subj_cat), for the latest year and a comparison year.
        def families(sy):
            # A blank sittings cell is DESE SUPPRESSION of a small group, not zero. The
            # performance file carries the same count as tests_taken and is often not
            # suppressed; where it is, the family is marked unknown rather than zero.
            rows = q(db, "SELECT subj_cat family, tests_taken_cnt sittings, test_takers_cnt takers FROM dese_ap WHERE kind='participation' AND org_type='District' "
                         "AND org_name=? AND stu_grp='All Students' AND sy=? AND subj=subj_cat AND subj!='All Subjects'", DISTRICT, sy)
            perf_rows = {r['family']: r['tests'] for r in q(db, "SELECT subj_cat family, tests_taken tests FROM dese_ap WHERE kind='performance' AND org_type='District' "
                                                                  "AND org_name=? AND stu_grp='All Students' AND sy=? AND subj=subj_cat AND subj!='All Subjects'", DISTRICT, sy)}
            out = {}
            for r in rows:
                if r['sittings'] is not None:
                    out[r['family']] = dict(sittings=int(r['sittings']), takers=int(r['takers'] or 0), basis='participation')
                elif perf_rows.get(r['family']) is not None:
                    out[r['family']] = dict(sittings=int(perf_rows[r['family']]), takers=int(r['takers'] or 0), basis='performance file (participation suppressed)')
                else:
                    out[r['family']] = dict(sittings=None, takers=int(r['takers'] or 0), basis='suppressed by DESE')
            return out
        fam_last = families(last['sy'])
        compare_sy = 2015 if any(y['sy'] == 2015 for y in years) else first['sy']
        fam_then = families(compare_sy)
        fam_perf = {r['family']: r['pct_3_5'] for r in q(db, "SELECT subj_cat family, pct_3_5 FROM dese_ap WHERE kind='performance' AND org_type='District' "
                                                              "AND org_name=? AND stu_grp='All Students' AND sy=? AND subj=subj_cat AND subj!='All Subjects'", DISTRICT, last['sy'])}
        fams = sorted({*fam_last, *fam_then})
        family_rows = [dict(family=f, then=fam_then.get(f, {}).get('sittings'), now=fam_last.get(f, {}).get('sittings'),
                            takers_now=fam_last.get(f, {}).get('takers', 0), pass_share=fam_perf.get(f),
                            basis_now=fam_last.get(f, {}).get('basis', 'not reported'), basis_then=fam_then.get(f, {}).get('basis', 'not reported')) for f in fams]
        family_rows.sort(key=lambda r: -(r['now'] or 0))
        def tot(fam, names):
            vals = [fam.get(f, {}).get('sittings') for f in names]
            if any(v is None for v in vals):
                fail('a family needed for a conclusion is suppressed in both files: %s' % [n for n, v in zip(names, vals) if v is None])
            return sum(vals)
        humanities = tot(fam_last, ('English Language Arts', 'History and Social Science'))
        stem_now = tot(fam_last, ('Math and Computer Science', 'Science and Technology'))
        stem_then = tot(fam_then, ('Math and Computer Science', 'Science and Technology'))
        lang_now = tot(fam_last, ('Foreign Languages',))
        lang_then = tot(fam_then, ('Foreign Languages',))

        rows = [
            conclusion(
                id='two-in-five-upperclassmen-sit-an-ap-exam',
                claim='%s students sat at least one AP exam in SY%d — about %s of the 11th and 12th grades.'
                      % (C.num(last['takers']), last['sy'], C.pct(100 * last['share_1112'], 0)),
                so_what='In SY%d it was %s of a bigger class. The count peaked at %s in SY%d.'
                        % (first['sy'], C.pct(100 * first['share_1112'], 0), C.num(peak['takers']), peak['sy']),
                figures={'takers': figure(last['takers'], C.num(last['takers']), 'students sat an AP exam, SY%d' % last['sy']),
                         'share': figure(last['share_1112'], C.pct(100 * last['share_1112'], 0)),
                         'share_first': figure(first['share_1112'], C.pct(100 * first['share_1112'], 0)),
                         'takers_first': figure(first['takers'], C.num(first['takers'])), 'peak': figure(peak['takers'], C.num(peak['takers'])),
                         'sittings': figure(last['sittings'], C.num(last['sittings'])),
                         'g1112': figure(last['g1112'], C.num(last['g1112'])), 'g1112_first': figure(first['g1112'], C.num(first['g1112'])),
                         'sy': figure(last['sy'], 'SY%d' % last['sy']), 'sy_first': figure(first['sy'], 'SY%d' % first['sy']), 'sy_peak': figure(peak['sy'], 'SY%d' % peak['sy'])},
                figure='takers', kind='measured', bearing='sizes',
                lede='A smaller high school sends a larger share of its upperclassmen into AP exams than it did.',
                detail='%s students took %s exams in SY%d, against %s in the 11th and 12th grades. In SY%d it was %s students against %s. '
                       'The ratio is an approximation: a tenth grader can sit an exam, and the two DESE files count on different days.'
                       % (C.num(last['takers']), C.num(last['sittings']), last['sy'], C.num(last['g1112']), first['sy'], C.num(first['takers']), C.num(first['g1112'])),
                basis='`dese_ap` participation, Lunenburg district, All Students, All Subjects; `dese_enrollment` grades 11 and 12 for the denominator.',
                not_shown='Who is offered the courses, who is steered toward or away from the exam, or what a sitting costs a family. Participation is a count of who sat.',
                allow=('11th', '12th'),
                see=[('/what-courses-actually-ran', 'What courses actually ran'), ('/who-is-in-the-schools', 'Who is in the schools')],
            ),
            conclusion(
                id='the-pass-rate-is-the-highest-in-the-file',
                claim='%s of AP tests scored 3 or better in SY%d, the best of %s years; the low: %s in SY%d.'
                      % (C.pct(100 * best['pass_share']), best['sy'], C.num(len([y for y in years if y['pass_share'] is not None])), C.pct(100 * worst['pass_share']), worst['sy']),
                so_what='A score of 3 is the usual threshold for college credit. Two years ago it was %s.' % C.pct(100 * next(y for y in years if y['sy'] == last['sy'] - 2)['pass_share']),
                figures={'best': figure(best['pass_share'], C.pct(100 * best['pass_share']), 'of tests scored 3–5, SY%d' % best['sy']),
                         'worst': figure(worst['pass_share'], C.pct(100 * worst['pass_share'])),
                         'two_ago': figure(next(y for y in years if y['sy'] == last['sy'] - 2)['pass_share'], C.pct(100 * next(y for y in years if y['sy'] == last['sy'] - 2)['pass_share'])),
                         'years': figure(len([y for y in years if y['pass_share'] is not None]), C.num(len([y for y in years if y['pass_share'] is not None]))),
                         'sy_best': figure(best['sy'], 'SY%d' % best['sy']), 'sy_worst': figure(worst['sy'], 'SY%d' % worst['sy']),
                         'tests': figure(last['sittings'], C.num(last['sittings'])),
                         'fives': figure(last['scores'][4], C.num(last['scores'][4])), 'ones': figure(last['scores'][0], C.num(last['scores'][0])),
                         'sy': figure(last['sy'], 'SY%d' % last['sy'])},
                figure='best', kind='measured', bearing='sizes',
                detail='Of %s tests in SY%d, %s scored a five and %s scored a one; the full distribution is charted below. It is a share of TESTS, not of students: '
                       'a student who sat three exams counts three times.'
                       % (C.num(last['sittings']), last['sy'], C.num(last['scores'][4]), C.num(last['scores'][0])),
                basis='`dese_ap` performance, Lunenburg district, All Students, All Subjects, pct_3_5 and the score counts.',
                not_shown='Why. Better teaching, different students choosing to sit, or the mix of subjects shifting toward ones with higher pass rates all produce this number, and the file separates none of them.',
                allow=('3–5', 'score of 3', '3 or better'),
            ),
            conclusion(
                id='the-exams-are-english-and-history',
                claim='%s of %s AP sittings in SY%d were English or history; science and math were %s.'
                      % (C.num(humanities), C.num(last['sittings']), last['sy'], C.num(stem_now)),
                so_what='In SY%d science and math were %s sittings. Foreign languages: %s then, %s now.'
                        % (compare_sy, C.num(stem_then), C.num(lang_then), C.num(lang_now)),
                figures={'humanities': figure(humanities, C.num(humanities), 'English and history sittings, SY%d' % last['sy']),
                         'sittings': figure(last['sittings'], C.num(last['sittings'])), 'stem_now': figure(stem_now, C.num(stem_now)), 'stem_then': figure(stem_then, C.num(stem_then)),
                         'lang_now': figure(lang_now, C.num(lang_now)), 'lang_then': figure(lang_then, C.num(lang_then)),
                         'hum_share': figure(humanities / last['sittings'], C.pct(100 * humanities / last['sittings'], 0)),
                         'sy': figure(last['sy'], 'SY%d' % last['sy']), 'sy_then': figure(compare_sy, 'SY%d' % compare_sy)},
                figure='humanities', kind='measured', bearing='sizes',
                detail='%s of sittings in SY%d were in English or history. The table below gives every subject family at both ends. '
                       'This is the exam-room view of what /what-courses-actually-ran measures in the schedule: a language programme narrowing, and a STEM one that sits few exams.'
                       % (C.pct(100 * humanities / last['sittings'], 0), last['sy']),
                basis='`dese_ap` participation, subject-family rollups (DESE’s own, `subj = subj_cat`), Lunenburg district, SY%d and SY%d.' % (compare_sy, last['sy']),
                not_shown='Whether the courses are offered and unchosen, or not offered. A sitting count cannot tell a closed door from an empty room. '
                          'Small families are suppressed in DESE’s participation file and taken from its performance file, which says so in the table.',
                see=[('/what-courses-actually-ran', 'Foreign language, narrowing on every instrument')],
            ),
        ]
        return dict(
            generated_by='scripts/build_ap.py',
            about='Advanced Placement at Lunenburg High, SY%d to SY%d: who sits the exams, in what subjects, and how the tests score.' % (first['sy'], last['sy']),
            grain='Three counts that are not the same thing: CHILDREN who sat at least one exam, SITTINGS, and TESTS at each score. The participation ratio divides '
                  'children by the 11th and 12th grade enrolment and is an approximation.',
            first_sy=first['sy'], last_sy=last['sy'], compare_sy=compare_sy,
            years=years, families=family_rows,
            sources=documents(),
            not_established=[
                'Which AP courses the high school offers in a given year; DESE counts exams sat, not courses taught.',
                'Anything about the students who did not sit: whether they were in the course and chose not to, or never had access.',
                'How Lunenburg compares to other districts — the extract holds Lunenburg only.',
            ],
            conclusions=emit('ap', rows),
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
            print('STALE %s — run build_ap.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: SY%d–SY%d, %d conclusions' % (os.path.relpath(OUT, ROOT), data['first_sy'], data['last_sy'], len(data['conclusions'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
