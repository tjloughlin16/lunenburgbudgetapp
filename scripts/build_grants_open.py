#!/usr/bin/env python3
"""/grants-open-to-lunenburg: the DESE grant programs a school district can apply for now.

    python3 scripts/build_grants_open.py           # write fy28/public/data/grants-open-to-lunenburg.json
    python3 scripts/build_grants_open.py --check   # fail if it is stale

TJ, 22 October 2026: *"This page I hope to post the schools at to know they should be
applying."* So the page is a WORKING LIST for the district, not a report about it (rule 8):
it leads with what is open and who may apply, soonest due first, and says nothing about what
anybody did or did not apply for in the past -- nothing here could know that.

MODEL-DRIVEN (rule 7d). Everything comes from sources/data/dese-grant-opportunities.csv
(extract_dese_grants.py); the page lays out, it computes nothing. Every figure on the page is
a count of rows or a date DESE printed, formatted here.

WHAT IS OURS (rule 3). The grouping by `district_reading` is our reading of DESE's eligibility
text, and every card carries that text verbatim beside the reading and the rule that produced
it. Which grants are FORMULA money (DESE's own Grant Type: Entitlement or Allocation) is
DESE's label, not ours.
"""
import argparse
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV = os.path.join(ROOT, 'sources', 'data', 'dese-grant-opportunities.csv')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'grants-open-to-lunenburg.json')
LIST_URL = 'https://www.doe.mass.edu/grants/grants.aspx'
FORMULA = {'Entitlement', 'Allocation'}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']


def long_date(iso):
    if not iso:
        return ''
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, MONTHS[d.month - 1], d.year)


def n_word(n, one, many):
    return '%d %s' % (n, one if n == 1 else many)


def held_list(sha):
    """The DATED copy of the list holding these bytes -- the publisher's file, in the bucket --
    not the working copy, which is ours and is overwritten."""
    import glob
    import hashlib
    for p in sorted(glob.glob(os.path.join(ROOT, 'sources', 'state-dese', 'grants', '2*', 'grants*.html'))):
        if hashlib.sha256(open(p, 'rb').read()).hexdigest() == sha:
            return os.path.relpath(p, os.path.join(ROOT, 'sources'))
    raise SystemExit('no dated copy of the list matches the extract: run fetch_dese_grants.py')


def card(r):
    return dict(
        fund_code=r['fund_code'], program=r['program'], grant_type=r['grant_type'],
        funding=r['funding'].capitalize() if r['funding'] in ('state', 'federal', 'trust') else r['funding'],
        posted=r['posted'], posted_text=long_date(r['posted']),
        due=r['due'], due_text=long_date(r['due']),
        unit=r['unit'], contact=r['contact'], purpose=r['purpose'],
        funding_text=r['funding_text'], eligibility=r['eligibility'],
        reading=r['district_reading'], basis=r['reading_basis'], url=r['detail_url'])


def build():
    rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
    if not rows:
        raise SystemExit('no rows in %s' % CSV)
    as_of = rows[0]['fetched']
    if any(r['fetched'] != as_of for r in rows):
        raise SystemExit('rows from more than one look in %s' % CSV)
    soon = lambda rs: sorted(rs, key=lambda r: (r['due'] or '9999', r['program']))  # noqa: E731
    is_open = lambda r: r['open_on_list_date'] == 'yes'  # noqa: E731
    applied = [r for r in rows if r['grant_type'] not in FORMULA]
    groups = [
        ('open-districts', 'Open now: school districts may apply',
         'DESE’s eligibility text opens these to public school districts. Conditions, where '
         'there are any, are in the text on each card.',
         soon([r for r in applied if is_open(r) and r['district_reading'] == 'districts eligible'])),
        ('open-unclear', 'Open now: limited to named or past recipients, or unclear',
         'Open, but the eligibility text limits them to recipients DESE or the state budget '
         'names, or to last year’s grantees, or does not say plainly. None names Lunenburg.',
         soon([r for r in applied if is_open(r) and r['district_reading'] == 'unclear'])),
        ('open-not', 'Open now: not for school districts',
         'The eligibility text names only other kinds of applicant.',
         soon([r for r in applied if is_open(r) and r['district_reading'] == 'not districts'])),
        ('formula', 'Formula grants: money the district receives, not competes for',
         'DESE lists these as Entitlement or Allocation grants. The amount is set by formula; '
         'the district files an application to draw it. Separate from the competitive grants above.',
         soon([r for r in rows if r['grant_type'] in FORMULA])),
        ('closed', 'Still on DESE’s list, past their due date',
         'DESE keeps a program on its list for a while after it closes. Useful as a guide to '
         'what may come round again next year.',
         sorted([r for r in applied if not is_open(r)], key=lambda r: r['due'] or '', reverse=True)),
    ]
    lead = groups[0][3]
    stats = [
        dict(value=str(len(lead)),
             label='%s open to school districts on %s' % ('grant' if len(lead) == 1 else 'grants',
                                                          long_date(as_of))),
        dict(value=long_date(lead[0]['due']) if lead else 'none',
             label='the soonest due date among them'),
        dict(value=str(len(rows)), label='programs on DESE’s current-grants list that day'),
    ]
    return {
        'as_of': as_of, 'as_of_text': long_date(as_of),
        'listed': len(rows),
        'stats': stats,
        'groups': [dict(id=i, title=t, note=n, rows=[card(r) for r in rs]) for i, t, n, rs in groups],
        'reading_note': ('Which group a grant is in is OUR reading of DESE’s eligibility text, '
                         'by fixed rules that lean to “unclear” when in doubt. The text itself, '
                         'quoted on every card, is what decides; check it, and the program page, '
                         'before relying on the grouping.'),
        'grain': ('One row per program on DESE’s “Current Grants” list, as DESE listed them on %s, '
                  'with the eligibility, purpose and funding quoted from each program’s own page. '
                  'DESE publishes only the current list; the copies this site keeps each week, '
                  'when anything changes, are the only history of it.' % long_date(as_of)),
        'sources': [
            {'label': 'DESE: Find All Current Grant Funding Opportunities', 'url': LIST_URL},
            {'label': 'Our copy of that list, as fetched', 'url': '/docs/' + held_list(rows[0]['list_sha256'])},
            {'label': 'Our table of every program on it, with our reading of eligibility',
             'url': '/docs/data/dese-grant-opportunities.csv'},
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    p = build()
    text = json.dumps(p, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if a.check:
        have = open(PAYLOAD, encoding='utf-8').read() if os.path.exists(PAYLOAD) else None
        if have != text:
            print('STALE: %s' % os.path.relpath(PAYLOAD, ROOT))
            return 1
        print('ok: payload reproduces')
        return 0
    tmp = PAYLOAD + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(text)
    os.replace(tmp, PAYLOAD)
    for g in p['groups']:
        print('  %-15s %d' % (g['id'], len(g['rows'])))
    print('wrote %s' % os.path.relpath(PAYLOAD, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
