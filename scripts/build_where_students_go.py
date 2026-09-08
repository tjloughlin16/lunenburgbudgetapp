#!/usr/bin/env python3
"""Where Lunenburg's children actually go to school.

WHY THIS IS NOT `/if-students-leave`. That page is a SCENARIO -- what school choice would
cost the town if students transferred out, with every input a dial. It answers a question
somebody put to this site. This one answers a different question and answers it with a
measurement: where do the town's children go now, where did they go before, and by which
route.

A scenario and a record must not share a page. The scenario's numbers are ours and the
record's are DESE's, and the fastest way to turn an estimate into a fact is to print it
beside one.

THE THREE ROUTES ARE THREE DIFFERENT MECHANISMS, and the page never sums them into "kids
leaving" without saying so:

  * MONTY TECH is not choosing out. Lunenburg is a MEMBER TOWN of the Montachusett
    Regional Vocational Technical district, so those students appear as `Resident/Member`
    -- the town is assessed for them whether or not it likes the number, and no
    Lunenburg decision admits or refuses them.
  * SCHOOL CHOICE is a family applying to another district that has opened seats. The
    sending town pays tuition out of its cherry sheet.
  * CHARTER is a family applying to a charter school. Different statute, different money.

WHAT THE DATA CANNOT DO, and it is the question everybody asks: BY GRADE. DESE publishes
this by receiving district and year and not by grade, and the grade counts that exist are
headcounts inside a district rather than an outflow from a town, so they cannot be
differenced to recover it. Registered in money-gaps.csv. The plausible story -- that
choice-outs cluster at grade 9 when families pick a high school -- is a hypothesis nothing
here tests, and rule 7 says it does not get written as though it were a finding.

    python3 scripts/build_where_students_go.py
    python3 scripts/build_where_students_go.py --check
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'where-students-go.json')
MIN_YEARS = 10


def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)

    years = [r[0] for r in db.execute(
        "SELECT DISTINCT fy FROM dese_town_enrollment WHERE town LIKE 'Lunenburg%' "
        "ORDER BY fy")]
    if len(years) < MIN_YEARS:
        raise SystemExit('only %d years of town enrolment; expected at least %d. '
                         'Nothing written.' % (len(years), MIN_YEARS))

    # THE ROUTE LABELS ARE DESE'S, NOT OURS. Read them off the data rather than mapping
    # them in code, so a new reason appears the day DESE starts publishing it instead of
    # being silently dropped into whatever bucket a dictionary happened to have.
    reasons = [r[0] for r in db.execute(
        "SELECT DISTINCT enrollment_reason FROM dese_town_enrollment "
        "WHERE town LIKE 'Lunenburg%' ORDER BY enrollment_reason")]
    if not reasons:
        raise SystemExit('no enrolment reasons found for Lunenburg. Nothing written.')

    series = []
    for fy in years:
        by_reason = {r: n for r, n in db.execute(
            "SELECT enrollment_reason, SUM(students) FROM dese_town_enrollment "
            "WHERE town LIKE 'Lunenburg%' AND fy=? GROUP BY enrollment_reason", (fy,))}
        monty = db.execute(
            "SELECT COALESCE(SUM(students),0) FROM dese_town_enrollment "
            "WHERE town LIKE 'Lunenburg%' AND fy=? AND district LIKE 'Montachusett%'",
            (fy,)).fetchone()[0]
        resident = by_reason.get('Resident/Member', 0)
        choice = by_reason.get('School Choice Program', 0)
        charter = by_reason.get('Charter School', 0)
        other = sum(v for k, v in by_reason.items()
                    if k not in ('Resident/Member', 'School Choice Program',
                                 'Charter School'))
        series.append({
            'fy': fy,
            'in_district': resident - monty,
            'monty_tech': monty,
            'school_choice': choice,
            'charter': charter,
            'other_routes': other,
            'outside': monty + choice + charter + other,
            'resident_total': resident + choice + charter + other,
        })

    # Destinations, latest year, named.
    latest = years[-1]
    dests = [{'district': d, 'reason': r, 'students': n} for d, r, n in db.execute(
        "SELECT district, enrollment_reason, students FROM dese_town_enrollment "
        "WHERE town LIKE 'Lunenburg%' AND fy=? AND district NOT LIKE 'Lunenburg%' "
        "AND students > 0 ORDER BY students DESC", (latest,))]
    if not dests:
        raise SystemExit('no receiving districts for FY%d. A join that matches nothing '
                         'looks exactly like a town nobody leaves. Nothing written.'
                         % latest)

    first, last = series[0], series[-1]

    def pct(a, b):
        return round(100.0 * (b - a) / a, 1) if a else None

    return {
        'about': 'Where Lunenburg resident students go to school, by route and by '
                 'receiving district, from DESE’s town-level enrolment reporting.',
        'source': {
            'table': 'dese_town_enrollment',
            'publisher': 'Massachusetts Department of Elementary and Secondary Education',
            'note': 'DESE publishes this as two datasets, Sending and Receiving. Compared '
                    'row by row they hold identical rows and differ only in column order, '
                    'so it is loaded once — a net position here rests on one measurement '
                    'rather than on two agreeing ones.',
        },
        'fy_first': first['fy'], 'fy_last': last['fy'],
        'reasons_published': reasons,
        'series': series,
        'destinations_latest': dests,
        'latest': last,
        'change': {
            'monty_tech_pct': pct(first['monty_tech'], last['monty_tech']),
            'school_choice_pct': pct(first['school_choice'], last['school_choice']),
            'charter_pct': pct(first['charter'], last['charter']),
            'outside_pct': pct(first['outside'], last['outside']),
            'in_district_pct': pct(first['in_district'], last['in_district']),
        },
        'three_routes': [
            {'route': 'Montachusett Regional (Monty Tech)',
             'what': 'NOT choosing out. Lunenburg is a member town of the regional '
                     'vocational district, so these students are reported as '
                     'Resident/Member. The town is assessed for them, and no Lunenburg '
                     'decision admits or refuses any of them.'},
            {'route': 'School choice',
             'what': 'A family applies to another district that has opened seats. The '
                     'sending town pays tuition, taken off its cherry sheet.'},
            {'route': 'Charter schools',
             'what': 'A family applies to a charter school. A different statute and a '
                     'different flow of money from school choice.'},
        ],
        'not_established': [
            'WHICH GRADES. DESE publishes this by receiving district and year, never by '
            'grade. The grade counts that exist are headcounts inside a district rather '
            'than an outflow from a town, so they cannot be differenced to recover it. '
            'Whether families leave at a transition year or steadily throughout is '
            'therefore unknown, and those imply very different things about what the '
            'district could change.',
            'WHY ANY FAMILY LEFT. Nothing here records a reason. A count of students is '
            'not a statement about programmes, buildings or satisfaction.',
            'WHETHER THE SAME CHILDREN STAY GONE. These are annual headcounts, not a '
            'cohort followed through time, so a stable total is equally consistent with '
            'the same families every year and with complete turnover.',
            'WHAT ANY OF IT COSTS. This page counts students. Dollars are a different '
            'quantity and a different page.',
        ],
        'closes': 'Grade-level outflow would be settled by DESE SIMS Report 7 or the '
                  'district’s own October 1 enrolment submission broken out by grade and '
                  'residence — filed annually, not published.',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()
    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT)); return 1
        with open(OUT, encoding='utf-8') as fh:
            if json.load(fh) != data:
                print('STALE %s — run: python3 scripts/build_where_students_go.py'
                      % os.path.relpath(OUT, ROOT)); return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT)); return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True); fh.write('\n')
    l, c = data['latest'], data['change']
    print('%s: FY%d–FY%d' % (os.path.relpath(OUT, ROOT), data['fy_first'], data['fy_last']))
    print('  FY%d: %d of %d resident students educated outside Lunenburg (%.1f%%)'
          % (l['fy'], l['outside'], l['resident_total'],
             100.0 * l['outside'] / l['resident_total']))
    print('  Monty Tech %d (%+.1f%%)  choice %d (%+.1f%%)  charter %d (%+.1f%%)'
          % (l['monty_tech'], c['monty_tech_pct'], l['school_choice'],
             c['school_choice_pct'], l['charter'], c['charter_pct']))
    print('  total outside %+.1f%% while its composition changed completely'
          % c['outside_pct'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
