#!/usr/bin/env python3
"""Every figure in the AP conclusions, recomputed from the database.

    python3 scripts/verify_ap.py
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'ap.json')
FAILS = []


def check(ok, msg):
    if not ok:
        FAILS.append(msg)


def main():
    d = json.load(open(OUT, encoding='utf-8'))
    by_id = {c['id']: c for c in d['conclusions']}
    f = lambda cid, k: by_id[cid]['figures'][k]['value']
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    part = db.execute("SELECT sy, test_takers_cnt, tests_taken_cnt FROM dese_ap WHERE kind='participation' AND org_type='District' AND org_name='Lunenburg' "
                      "AND stu_grp='All Students' AND subj='All Subjects' ORDER BY sy").fetchall()
    perf = {r[0]: r[1:] for r in db.execute("SELECT sy, pct_3_5, score_1, score_5 FROM dese_ap WHERE kind='performance' AND org_type='District' AND org_name='Lunenburg' "
                                              "AND stu_grp='All Students' AND subj='All Subjects'").fetchall()}
    last, first = part[-1], part[0]
    g = lambda sy: db.execute("SELECT grade_11_cnt+grade_12_cnt FROM dese_enrollment WHERE org_level='district' AND org_name='Lunenburg' AND fy=?", (sy,)).fetchone()[0]
    c = 'two-in-five-upperclassmen-sit-an-ap-exam'
    check(f(c, 'takers') == last[1] and f(c, 'sittings') == last[2], 'takers/sittings')
    check(abs(f(c, 'share') - last[1] / g(last[0])) < 1e-9 and abs(f(c, 'share_first') - first[1] / g(first[0])) < 1e-9, 'shares')
    check(f(c, 'peak') == max(p[1] for p in part), 'peak')
    c = 'the-pass-rate-is-the-highest-in-the-file'
    best = max(perf.items(), key=lambda kv: kv[1][0]); worst = min(perf.items(), key=lambda kv: kv[1][0])
    check(abs(f(c, 'best') - best[1][0]) < 1e-9 and f(c, 'sy_best') == best[0], 'best')
    check(abs(f(c, 'worst') - worst[1][0]) < 1e-9 and f(c, 'sy_worst') == worst[0], 'worst')
    check(f(c, 'fives') == perf[last[0]][2] and f(c, 'ones') == perf[last[0]][1], 'score counts')
    check(abs(f(c, 'two_ago') - perf[last[0] - 2][0]) < 1e-9, 'two years ago')
    c = 'the-exams-are-english-and-history'
    def fam(sy, name):
        r = db.execute("SELECT tests_taken_cnt FROM dese_ap WHERE kind='participation' AND org_type='District' AND org_name='Lunenburg' AND stu_grp='All Students' AND sy=? AND subj=? AND subj=subj_cat", (sy, name)).fetchone()
        if r and r[0] is not None:
            return r[0]
        r = db.execute("SELECT tests_taken FROM dese_ap WHERE kind='performance' AND org_type='District' AND org_name='Lunenburg' AND stu_grp='All Students' AND sy=? AND subj=? AND subj=subj_cat", (sy, name)).fetchone()
        return r[0] if r else None
    hum = fam(last[0], 'English Language Arts') + fam(last[0], 'History and Social Science')
    stem_now = fam(last[0], 'Math and Computer Science') + fam(last[0], 'Science and Technology')
    stem_then = fam(d['compare_sy'], 'Math and Computer Science') + fam(d['compare_sy'], 'Science and Technology')
    check(f(c, 'humanities') == hum and f(c, 'stem_now') == stem_now and f(c, 'stem_then') == stem_then, 'families')
    check(f(c, 'lang_now') == fam(last[0], 'Foreign Languages') and f(c, 'lang_then') == fam(d['compare_sy'], 'Foreign Languages'), 'languages')
    if FAILS:
        print('FAIL:\n  ' + '\n  '.join(FAILS)); return 1
    print('PASS — every figure the AP conclusions name recomputes from dese_ap and dese_enrollment')
    return 0


if __name__ == '__main__':
    sys.exit(main())
