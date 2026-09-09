#!/usr/bin/env python3
"""Special education, in FOUR reports that are deliberately not one report.

WHY FOUR. CLAUDE.md rule 5 records that special education is about 22% of school spending
and had NO page in this app for months, because "the district must place a child where the
plan requires" read like nothing to model. That reasoning is wrong: a line nobody controls
still sets the size of the problem. This closes that gap -- and the way it closes it is the
constraint, not a detail.

`notes/QUEUE.md` item 10: **"Four reports, not one. Keep them apart. Merging them into one
narrative is how a proxy becomes a fact."** The four questions are answered by four
different datasets at four different GRAINS, and every one of the sentences this project
has had to retract was made by sliding between two of them:

    students      a person-count DESE publishes, at a census date        person
    leaving       a town/district PAIR count, with no disability flag    town-pair
    cost          dollars, by fund, from a statutory return              dollars
    route         a placement COHORT followed to a destination           cohort

A student is not a dollar. A placement is not a cost. A resident who leaves under school
choice is not established to be a special education student -- the file carries no
disability flag at all. So this script writes FOUR payloads to four addresses, shares only
its provenance and its meeting-archive plumbing between them, and never computes a figure
that crosses two of them.

    python3 scripts/build_special_education.py
    python3 scripts/build_special_education.py --check

THE ROLLUP TRAP, rule 13. Every DESE file here carries a State row with DIST_CODE
00000000 beside the district detail. Summing them once produced $116M for a $26.6M
district. Every query below names `lea=?` or `geo_level='state'` explicitly, and the state
figures are used ONLY as a published benchmark, never added to anything.

WHAT THIS SCRIPT REFUSES TO DO, each because the data cannot carry it:

  * Divide a dollar by a student. Two of these datasets count children and one counts
    money, and they are drawn from different returns with different census rules.
  * Treat the school-choice count as a special education figure. It has no IEP flag.
  * Publish a DESE staff FTE row that does not reconcile against its own printed rate.
    Only the paraprofessional row does, in every year; the rest do not, in any year, and
    the script computes that rather than assuming it.
  * Sum the K-12 and K-2 trajectory rows. K-2 is a subset grade span, not a peer.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

# The conclusions each of these four reports states, as DATA rather than as sentences in
# a page. See scripts/conclusions.py: the generator that computed a figure writes the
# claim that rests on it, and nothing downstream may state more than the payload holds.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
LEA = '01620000'
# Montachusett Regional Vocational Technical. Lunenburg is a MEMBER of this district,
# which is why its children are Resident/Member rows and why they are not "choosing out".
MONTY = '08320000'
STATE = '00000000'
TOWN = 'Lunenburg'
MINUTES = 'sources/meetings/text'

OUTS = {
    'students': os.path.join(PUB, 'sped-students.json'),
    'leaving': os.path.join(PUB, 'sped-leaving.json'),
    'cost': os.path.join(PUB, 'sped-cost.json'),
    'route': os.path.join(PUB, 'sped-route.json'),
}

# A published series does not lose most of itself. If a query comes back short, something
# moved underneath and writing it would publish a truncated record as though it were whole.
MIN_YEARS = {'students': 6, 'leaving': 12, 'cost': 15, 'route': 8, 'cb': 18, 'place': 14,
             'move': 6}

# WHAT WAS SAID, rule 15a. Every quote is re-read out of the extracted minutes on each run
# and a miss is fatal: a quote is a claim about a document, and rule 13 says quote the
# source rather than your rendering of it. The extracted text is quoted EXACTLY, including
# where the PDF's own spacing broke a word -- "reimbu rsed" below is what the document
# renders to, and repairing it here would be the defect this rule exists to prevent.
#
# NONE OF THESE IS A MEASUREMENT. They are statements of intent, of belief and of concern,
# and each is placed beside the figure it bears on rather than against it.
QUOTES = [
    dict(key='backbone', page='students', board='school-committee', date='2024-01-24',
         kind='minutes', doc='6375',
         quote='they are the backbone of special education and without them the '
               'department cannot run',
         why='A parent, in the public comment on the FY25 budget, on the proposed '
             'paraprofessional cuts. Said in the year between the two largest falls in '
             'the state’s own paraprofessional FTE figure for Lunenburg. It '
             'establishes that people knew posts were at stake. It does not establish '
             'what the FTE return counts, which is the open question beside it.'),
    dict(key='addtwo', page='students', board='school-committee', date='2025-10-01',
         kind='minutes', doc='7432',
         quote='Ms. Brzozoski makes a motion to add two paraprofessional positions where '
               'needed, Ms Young seconds the motion, all approve',
         why='A vote to ADD posts, in the same school year DESE’s return reports the '
             'lowest paraprofessional FTE in the eight years it covers. Both are real. A '
             'vote to add positions and a state FTE return are different quantities '
             'measured by different people at different moments, and nothing here '
             'reconciles them.'),
    dict(key='fivethousand', page='leaving', board='school-committee', date='2024-05-01',
         kind='minutes', doc='6554',
         quote='We receive $5000 per student, however the cost per student is more than '
               'that',
         why='The district on the money that arrives with a child choosing IN. The '
             'counts on this page are children, not dollars; this is the nearest the '
             'meeting record comes to a rate, and it is the receiving side rather than '
             'the sending side that the town is assessed for.'),
    dict(key='disentangle', page='leaving', board='school-committee', date='2026-03-23',
         kind='minutes', doc='7732',
         quote="the idea of bringing back things like vocational programs to the "
               "school, even if it means that we'd have to disentangle ourselves from "
               "Monty Tech that is something that has real long-term value",
         why='RULE 15a. The Monty Tech line is the one that MOVED on this page — the '
             'largest route out and the only one that rose — and this is what the '
             'School Committee was saying about it in the same year the count reached '
             'its high. It is a member’s view of what the town should do, offered in a '
             'discussion of school property and programmes. It is NOT evidence about '
             'why any of those children enrolled there, and it does not bear on the '
             'count at all: Lunenburg is assessed for its member share whatever anybody '
             'at this meeting thinks of the arrangement.'),
    dict(key='hsonly', page='leaving', board='school-committee', date='2026-02-04',
         kind='minutes', doc='7634',
         quote='We are looking to only add school choice options to the high school',
         why='School choice runs in both directions and the district decides how many '
             'seats to OPEN. This page counts only the children going the other way, and '
             'the decision quoted here is about the seats coming in.'),
    dict(key='eightyk', page='cost', board='school-committee', date='2024-01-24',
         kind='minutes', doc='6375',
         quote='We do get reimbu rsed for transportation through Circuit Breaker, for our '
               'Special Education transportation, last year that was about $80,000',
         why='The district’s own account of the transport reimbursement, said in '
             'January 2024. DESE’s published transport reimbursement for FY2024 is '
             'computed on this page; the two are close, and they are different '
             'quantities — a figure recalled at a meeting against a state payment '
             'schedule. The broken word is what the extracted document renders to.'),
    dict(key='fortyfour', page='cost', board='school-committee', date='2025-05-07',
         kind='minutes', doc='7207',
         quote='75% reimbursement for FY25 out of district special education '
               'transportation costs through the circuit breaker program increased from '
               '44%',
         why='The rate change, named at the meeting in the same year DESE’s file '
             'carries a supplemental payment comment for Lunenburg. It is the clearest '
             'case on this page of the reimbursement moving for a reason that has '
             'nothing to do with what any placement cost.'),
    dict(key='skyrocket', page='cost', board='school-committee', date='2024-01-24',
         kind='minutes', doc='6375',
         quote='Our out of District placements have skyrocketed',
         why='Said in January 2024. Both halves of this page bear on it and they point '
             'different ways: the DOLLARS did rise steeply into FY2024, and the town’s '
             'own published COUNT of placements went from 7 to 8. Dollars are not '
             'students. The sentence is true of one of those quantities and not of the '
             'other, which is the whole reason these are four reports.'),
    dict(key='radar', page='route', board='school-committee', date='2026-02-04',
         kind='minutes', doc='7634',
         quote='we currently have students on our radar that may require out of district '
               'placement and we have also had students move into the district that '
               'require out of district placements',
         why='The second half is the one this page cannot see. A cohort followed from an '
             'in-district placement measures the route through the district’s own '
             'settings; a child who arrives already placed enters the count without ever '
             'appearing in that cohort.'),
]

# The terms run against the meeting archive, per page. NOT typed counts -- a grep that
# finds nothing prints nothing, and nothing reads as "nobody said it".
SEARCHED = {
    'students': ['special education', 'IEP', 'paraprofessional', 'students with disabilities'],
    'leaving': ['school choice', 'charter', 'Monty Tech', 'Montachusett',
                'enrollment decline'],
    'cost': ['circuit breaker', 'out of district', 'tuition', 'Medicaid', 'extraordinary relief'],
    'route': ['out of district placement', 'inclusion', 'substantially separate',
              'collaborative'],
}


def q(db, sql, *a):
    return db.execute(sql, a).fetchall()


def fail(msg):
    raise SystemExit('%s. Nothing written.' % msg)


def need(rows, key, what):
    if len(rows) < MIN_YEARS[key]:
        fail('%s came back with %d rows; expected at least %d. A join that matches almost '
             'nothing looks exactly like a district that has almost no history'
             % (what, len(rows), MIN_YEARS[key]))
    return rows


# ----------------------------------------------------------------- provenance, rule 12

def manifest():
    with open(MANIFEST, encoding='utf-8') as fh:
        return {r['key']: r for r in csv.DictReader(fh)}


def doc(mf, key, table, publisher, note):
    r = mf.get(key)
    if not r:
        fail('%s is not in archive-manifest.csv. A figure without its document is not '
             'publishable' % key)
    return {'path': 'sources/' + key, 'sha256': r['sha256'], 'bytes': int(r['bytes']),
            'url': r['upstream'], 'docs_url': '/docs/' + key, 'table': table,
            'publisher': publisher, 'note': note}


DESE = 'Massachusetts Department of Elementary and Secondary Education'


# ------------------------------------------------------------- the meeting archive, 15a

def said_for(page):
    out = []
    for spec in QUOTES:
        if spec['page'] != page:
            continue
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here -- a quote on this page is attributed to a document that '
                 'is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s -- quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'],
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s%s%s-%s'
                 % (spec['date'][5:7], spec['date'][8:10], spec['date'][:4], spec['doc'])))
    if not out:
        fail('no quote is filed against the "%s" page -- rule 15a is a step, not an '
             'option' % page)
    return out


_ARCHIVE = {}


def archive():
    """Read the meeting archive once: the bodies, and the measured coverage denominator."""
    if _ARCHIVE:
        return _ARCHIVE
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here -- a search of nothing is not a search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    bodies, dates = [], []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            bodies.append(open(txt, encoding='utf-8', errors='replace').read())
            if r.get('date'):
                dates.append(r['date'])
    if not bodies or not dates:
        fail('no meeting document is readable -- refusing to publish a count of what '
             'nobody said')
    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here -- the searchable share '
             'cannot be typed')
    t = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            t[k] += int(r[k] or 0)
    if not t['searchable'] or t['held'] != t['searchable'] + t['unsearchable']:
        fail('minutes-searchable.csv does not reconcile -- refusing to publish a coverage '
             'figure that does not add up')
    _ARCHIVE.update(bodies=bodies, published=len(rows), text_files_present=len(bodies),
                    held=t['held'], searchable=t['searchable'],
                    unsearchable=t['unsearchable'], image_scan=t['image_scan'],
                    searchable_share=round(t['searchable'] / t['held'], 4),
                    first_date=min(dates), last_date=max(dates))
    return _ARCHIVE


def searched(page):
    a = archive()
    return [dict(term=t, documents=sum(1 for b in a['bodies']
                                       if re.search(re.escape(t), b, re.I)))
            for t in SEARCHED[page]]


def coverage():
    a = archive()
    return {k: a[k] for k in ('published', 'held', 'searchable', 'unsearchable',
                              'image_scan', 'searchable_share', 'text_files_present',
                              'first_date', 'last_date')}


# =====================================================================================
# 1. HOW MANY STUDENTS
# =====================================================================================

def build_students(db, mf):
    """A published COUNT of children on an IEP -- and the three counts that are not it."""
    # The count, and the enrollment it sits in. `dese_sped_program`, category `Enrollment`,
    # whose own total row is `Total In- and Out-of-District Students`.
    enrol = need(q(db, """
        SELECT fy,
               MAX(CASE WHEN indicator='Students with Disabilities' THEN measure_cnt END),
               MAX(CASE WHEN indicator='Total In- and Out-of-District Students'
                        THEN denominator_cnt END)
        FROM dese_sped_program
        WHERE lea=? AND geo_level='district' AND indicator_category='Enrollment'
        GROUP BY fy ORDER BY fy""", LEA), 'students', 'the SWD enrollment rows')

    # In district against out of district, from the SAME file and the same total.
    io = dict(((fy, ind), cnt) for fy, ind, cnt in q(db, """
        SELECT fy, indicator, measure_cnt FROM dese_sped_program
        WHERE lea=? AND geo_level='district'
              AND indicator_category='In District/Out of District'""", LEA))
    if not io:
        fail('the in-district / out-of-district join matched nothing')

    counts, mismatch = [], []
    for fy, swd, total in enrol:
        ind = io.get((fy, 'In-District'))
        ood = io.get((fy, 'Out-of-District'))
        tot = io.get((fy, 'Total Students with Disabilities'))
        if swd is None or ind is None or ood is None or tot is None:
            fail('FY%d is missing one of the four published counts -- refusing to publish '
                 'a partial reconciliation' % fy)
        if abs(tot - swd) > 0.5 or abs((ind + ood) - tot) > 0.5:
            mismatch.append(fy)
        counts.append({'fy': fy, 'swd': int(swd), 'enrolled': int(total),
                       'in_district': int(ind), 'out_of_district': int(ood),
                       'share_pct': round(100.0 * swd / total, 2)})

    # THE RATIO DENOMINATOR. DESE publishes its special education staffing as a rate per
    # 100 SWD, and `money-gaps.csv` records that the denominator behind those rates is
    # twelve lower than the count published beside it -- as an unexplained disagreement.
    # It is not unexplained: the difference is the published out-of-district count, in
    # every year. Computed here rather than asserted, and the residual is published.
    ratio_base = dict(q(db, """
        SELECT fy, measure_cnt FROM dese_sped_indicator
        WHERE lea=? AND geo_level='district'
              AND indicator='Special education paraprofessionals per 100 SWD'""", LEA))
    denom = []
    for c in counts:
        base = ratio_base.get(c['fy'])
        if base is None:
            continue
        denom.append({'fy': c['fy'], 'ratio_base': int(base),
                      'in_district': c['in_district'], 'total': c['swd'],
                      'residual': int(base) - c['in_district']})
    if not denom:
        fail('the staffing-ratio denominator join matched nothing')
    denom_all_match = all(d['residual'] == 0 for d in denom)

    # THE PARAPROFESSIONAL FTE, AND ONLY IT. Every row in this category prints an FTE, a
    # count and a rate; the rate reproduces from the other two for paraprofessionals in
    # every year and for no other staff category in any year. Measured here, published as
    # a finding, and the failing rows are NOT published as figures.
    staff = q(db, """
        SELECT fy, indicator, denominator_cnt, measure_cnt, measure_pct
        FROM dese_sped_indicator
        WHERE lea=? AND geo_level='district' AND indicator_category='SPECIAL EDUCATION STAFF'
              AND value_type='FTE per 100 SWD'
        ORDER BY fy, indicator""", LEA)
    if not staff:
        fail('the special education staff join matched nothing')
    recon = collections.defaultdict(lambda: [0, 0])
    paras = []
    for fy, ind, fte, base, rate in staff:
        if fte is None or base is None or rate is None:
            continue
        ok = abs(round(100.0 * fte / base, 1) - rate) < 0.051
        recon[ind][1] += 1
        recon[ind][0] += 1 if ok else 0
        if 'paraprofessional' in ind.lower():
            if not ok:
                fail('the paraprofessional rate for FY%d no longer reproduces from its '
                     'own FTE and count -- the one staff row this page publishes is the '
                     'one that reconciled' % fy)
            paras.append({'fy': fy, 'fte': fte, 'swd_base': int(base),
                          'per_100': rate})
    if len(paras) < MIN_YEARS['students']:
        fail('only %d years of paraprofessional FTE' % len(paras))
    staff_recon = sorted(({'indicator': k, 'reproduces': v[0], 'years': v[1]}
                          for k, v in recon.items()), key=lambda r: r['indicator'])
    if any(r['reproduces'] != r['years'] for r in staff_recon
           if 'paraprofessional' in r['indicator'].lower()):
        fail('a paraprofessional year failed reconciliation after the row-level check')

    # A THIRD COUNT, from a third file, which does NOT reconcile with the other two.
    move = need(q(db, """
        SELECT fy, enrolled_cnt, on_iep_cnt, moved_in_cnt, moved_out_cnt, repeats_prior_year
        FROM dese_sped_movement
        WHERE lea=? AND geo_level='district' AND grades='K-12' ORDER BY fy""", LEA),
        'move', 'the caseload movement rows')
    third = [{'fy': fy, 'enrolled': int(e), 'on_iep': int(i), 'moved_in': int(mi),
              'moved_out': int(mo), 'repeats_prior_year': rp == 'yes'}
             for fy, e, i, mi, mo, rp in move]
    by_fy = {c['fy']: c for c in counts}
    third_gap = [{'fy': t['fy'], 'movement': t['on_iep'], 'program': by_fy[t['fy']]['swd'],
                  'difference': t['on_iep'] - by_fy[t['fy']]['swd']}
                 for t in third if t['fy'] in by_fy]
    if not third_gap:
        fail('the two student counts share no year -- nothing to compare')

    # WHAT THE CHILDREN ARE, by DESE's own disability categories. `Disability Type All` is
    # the uncollapsed version; `Disability Type` folds several into "Other Disability" and
    # is not used, because a category that exists in one rendering and not the other would
    # look like a change in the population.
    dis = q(db, """
        SELECT fy, indicator, measure_cnt, denominator_cnt FROM dese_sped_program
        WHERE lea=? AND geo_level='district' AND indicator_category='Disability Type All'
              AND indicator <> 'Total Students with Disabilities'
        ORDER BY fy, indicator""", LEA)
    if not dis:
        fail('the disability-type join matched nothing')
    disability = [{'fy': fy, 'kind': ind, 'count': int(c),
                   'share_pct': round(100.0 * c / d, 2)} for fy, ind, c, d in dis]

    # PLACEMENT, and the shortfall published with it. This category is in-district only
    # and its parts run short of the total printed beside them; the gap is computed and
    # shown rather than the rows being presented as a breakdown of the whole.
    plc = q(db, """
        SELECT fy, indicator, measure_cnt, denominator_cnt FROM dese_sped_program
        WHERE lea=? AND geo_level='district' AND indicator_category='Placement'
        ORDER BY fy, indicator""", LEA)
    if not plc:
        fail('the placement join matched nothing')
    placement, ptot = [], collections.defaultdict(float)
    for fy, ind, c, d in plc:
        if ind == 'Total Students with Disabilities':
            continue
        placement.append({'fy': fy, 'setting': ind, 'count': int(c),
                          'share_pct': round(100.0 * c / d, 2)})
        ptot[fy] += c
    short = [{'fy': c['fy'], 'parts': int(ptot[c['fy']]), 'total': c['swd'],
              'in_district': c['in_district'],
              'unaccounted': c['swd'] - int(ptot[c['fy']])}
             for c in counts if c['fy'] in ptot]

    span = q(db, """
        SELECT fy, indicator, measure_cnt FROM dese_sped_program
        WHERE lea=? AND geo_level='district' AND indicator_category='Grade Span'
              AND indicator <> 'Total Students with Disabilities'
        ORDER BY fy, indicator""", LEA)
    grade_span = [{'fy': fy, 'span': ind, 'count': int(c)} for fy, ind, c in span]

    first, last = counts[0], counts[-1]
    lowest = min(counts, key=lambda c: c['swd'])
    share_points = round(last['share_pct'] - lowest['share_pct'], 2)
    # The share moved for two reasons and a reader deserves both. This holds the
    # denominator still, so the part of the movement that is the count is visible on its
    # own. It is a counterfactual and it is arithmetic on two published counts, not a
    # model: the same operation /peer-spending does to separate spending from enrollment.
    share_at_old_enrollment = round(100.0 * last['swd'] / lowest['enrolled'], 2)
    # An FTE is printed to one decimal by DESE and is not a dollar or a count, so it gets
    # its own rendering rather than being pushed through num() and losing the '.0'.
    ftes = '%.1f'
    para_first_fte, para_last_fte = ftes % paras[0]['fte'], ftes % paras[-1]['fte']
    para_first_100, para_last_100 = ftes % paras[0]['per_100'], ftes % paras[-1]['per_100']
    para_fall_pct = round(100.0 * (1 - paras[-1]['fte'] / paras[0]['fte']), 1)
    return {
        'about': 'How many Lunenburg children have an individual education programme, '
                 'from the count DESE publishes rather than from any dollar figure.',
        'grain': 'A count of children, at DESE’s census date. Not dollars, not FTE, '
                 'not placements.',
        'sources': [
            doc(mf, 'state-dese/dese-sped-program-characteristics.xlsx',
                'dese_sped_program', DESE,
                'Special Education Program Characteristics and Student Demographics '
                '(n62c-bx65). Carries the published count itself, not a percentage.'),
            doc(mf, 'state-dese/dese-sped-indicators.xlsx', 'dese_sped_indicator', DESE,
                'Special Education Indicators (yamx-769q). The staffing rates per 100 '
                'students with disabilities.'),
            doc(mf, 'state-dese/dese-sped-movement.xlsx', 'dese_sped_movement', DESE,
                'Students Moving In and Out of Special Education Services (8aww-sugs). '
                'A THIRD count, on a different basis.'),
        ],
        'fy_first': first['fy'], 'fy_last': last['fy'],
        'counts': counts,
        'counts_reconcile': not mismatch,
        'counts_mismatch_years': mismatch,
        'first': first, 'last': last, 'lowest': lowest,
        'change_count': last['swd'] - lowest['swd'],
        'change_share_points': round(last['share_pct'] - lowest['share_pct'], 2),
        'denominator': denom,
        'denominator_all_match': denom_all_match,
        'paras': paras,
        'para_first': paras[0], 'para_last': paras[-1],
        'staff_reconciliation': staff_recon,
        'third_count': third,
        'third_count_gap': third_gap,
        'disability': disability,
        'placement': placement,
        'placement_shortfall': short,
        'grade_span': grade_span,
        'conclusions': emit('how-many-students-are-on-an-iep', [
            conclusion(
                id='the-share-rose-partly-because-enrollment-fell',
                claim='Lunenburg children with a special education plan, %s'
                      % C.fy(last['fy']),
                so_what='Up from %s four years earlier. Enrollment fell over the same '
                        'years, so the share rose further than the count.'
                        % C.num(lowest['swd']),
                lede='%s Lunenburg children had a special education plan in %s, against '
                      '%s in %s \u2014 and because the number of children in the schools '
                      'fell over those years, the SHARE with a plan rose further than the '
                      'number did.'
                      % (C.num(last['swd']), C.fy(last['fy']), C.num(lowest['swd']),
                         C.fy(lowest['fy'])),
                detail='%s more children, on an enrollment that went from %s to %s. The '
                       'share therefore moved from %s to %s \u2014 %s. Both halves of '
                       'that matter to anyone reading a rising percentage as a rising '
                       'caseload: the caseload did rise, and had enrollment held where it '
                       'was the share would read %s rather than %s. These are '
                       'DESE\u2019s own published counts, not a percentage multiplied '
                       'back out.'
                       % (C.num(last['swd'] - lowest['swd']), C.num(lowest['enrolled']),
                          C.num(last['enrolled']), C.pct(lowest['share_pct']),
                          C.pct(last['share_pct']), C.points(share_points),
                          C.pct(share_at_old_enrollment), C.pct(last['share_pct'])),
                figures={
                    'last': figure(last['swd'], C.num(last['swd']), 'children'),
                    'last_fy': figure(last['fy'], C.fy(last['fy'])),
                    'low': figure(lowest['swd'], C.num(lowest['swd'])),
                    'low_fy': figure(lowest['fy'], C.fy(lowest['fy'])),
                    'change': figure(last['swd'] - lowest['swd'],
                                     C.num(last['swd'] - lowest['swd'])),
                    'enrolled_from': figure(lowest['enrolled'], C.num(lowest['enrolled'])),
                    'enrolled_to': figure(last['enrolled'], C.num(last['enrolled'])),
                    'share_from': figure(lowest['share_pct'], C.pct(lowest['share_pct'])),
                    'share_to': figure(last['share_pct'], C.pct(last['share_pct'])),
                    'share_points': figure(share_points, C.points(share_points)),
                    'share_at_old_enrollment': figure(share_at_old_enrollment,
                                                     C.pct(share_at_old_enrollment)),
                },
                figure='last',
                kind='measured',
                basis='DESE\u2019s Special Education Program Characteristics file for '
                      'Lunenburg, district rows only, every year it has been published.',
                not_shown='That a rising count means rising need. A count of children with '
                          'an IEP is a count of children who have one; referral, '
                          'evaluation and eligibility practice all move it and none of '
                          'them is published.',
                see=[('/what-special-education-costs', 'what it costs')],
            ),
            conclusion(
                id='paraprofessional-fte-fell-while-the-count-did-not',
                claim='Fall in the paraprofessionals the state counts in special '
                      'education',
                so_what='%s posts down to %s since %s, while the number of children they '
                        'support barely moved.'
                        % (para_first_fte, para_last_fte, C.fy(paras[0]['fy'])),
                lede='The state counts %s full-time paraprofessionals in Lunenburg\u2019s '
                      'special education programme, down from %s \u2014 a fall of %s, '
                      'while the number of children they support barely moved.'
                      % (para_last_fte, para_first_fte, C.pct(para_fall_pct)),
                detail='For every hundred children with a special education plan that is '
                       '%s posts falling to %s, over a group of children that went from %s '
                       'to %s. Paraprofessionals are the staff this budget grows fastest '
                       'in, and they are what this project\u2019s own forecast of '
                       'in-district special education costs is built on, so which way this '
                       'series runs changes what anybody planning from it should expect. '
                       'A full-time equivalent is a share of a post rather than a person: '
                       'the state counts assignments, so two half-time posts and one '
                       'full-time post are the same figure here.'
                       % (para_first_100, para_last_100,
                          C.num(paras[0]['swd_base']), C.num(paras[-1]['swd_base'])),
                figure='fall',
                figures={
                    'fall': figure(para_fall_pct, C.pct(para_fall_pct)),
                    'first_fy': figure(paras[0]['fy'], C.fy(paras[0]['fy'])),
                    'fte_from': figure(paras[0]['fte'], para_first_fte,
                                       'full-time equivalent posts'),
                    'fte_to': figure(paras[-1]['fte'], para_last_fte,
                                     'full-time equivalent posts'),
                    'per100_from': figure(paras[0]['per_100'], para_first_100),
                    'per100_to': figure(paras[-1]['per_100'], para_last_100),
                    'base_from': figure(paras[0]['swd_base'], C.num(paras[0]['swd_base'])),
                    'base_to': figure(paras[-1]['swd_base'], C.num(paras[-1]['swd_base'])),
                },
                kind='measured',
                basis='DESE\u2019s Special Education Indicators file. This is the one row '
                      'of that table that reproduces from its own printed FTE and count in '
                      'every year, which is why it is the only one published here.',
                not_shown='That posts were removed. An FTE series is a count of what was '
                          'CODED as a paraprofessional, and recoding, a change of funding '
                          'source, or a change of reporting rule would each produce this '
                          'same fall. Nothing published distinguishes them.',
                see=[('/school-staffing', 'the people the budget buys')],
            ),
        ]),
        'said': said_for('students'),
        'searched': searched('students'),
        'minutes': coverage(),
        'not_established': [
            'That a rising count means rising need. A count of children with an IEP is a '
            'count of children who have one. Referral, evaluation and eligibility '
            'practice all move it, and none of them is published here.',
            'What the special education FTE return counts. Only the paraprofessional row '
            'reproduces from its own printed FTE and count; the teacher, service and '
            'support rows in the same table do not, in any year, so they are not '
            'published as figures on this page.',
            'That the paraprofessional FTE series is a count of posts. `money-gaps.csv` '
            'already records that DESE’s FTE and the district’s '
            'paraprofessional budget line cannot describe the same population, and that '
            'DESE’s special education teacher FTE for Lunenburg falls 90% while '
            'total teacher FTE holds flat — a signature that recoding would produce '
            'exactly.',
            'How the third count relates to the other two. `dese_sped_movement` reports a '
            'K-12 grade-row basis and a different enrollment; nothing published states the '
            'census date or the inclusion rule behind either.',
            'A breakdown of every child by setting. DESE’s Placement category is '
            'in-district only and its parts run short of the total printed beside them; '
            'the shortfall is published on this page rather than hidden by rescaling.',
        ],
        'closes': 'DESE’s SIMS submission detail for Lunenburg, stating the census '
                  'date and the inclusion rule behind each published count, and the '
                  'EPIMS work assignment records that would say what a special education '
                  'FTE is a count of.',
    }


# =====================================================================================
# 2. HOW MANY LEAVE, AND WHERE
# =====================================================================================

def build_leaving(db, mf):
    """Every resident child who is educated somewhere else -- and NOT a sped figure."""
    rows = q(db, """
        SELECT fy, enrollment_reason, district, lea, students FROM dese_town_enrollment
        WHERE town=? ORDER BY fy, enrollment_reason, district""", TOWN)
    if not rows:
        fail('the town enrollment join matched nothing')
    years = sorted({r[0] for r in rows})
    need([(y,) for y in years], 'leaving', 'the town enrollment years')

    # ELSEWHERE IS "NOT ENROLLED IN THE LUNENBURG DISTRICT", NOT "NOT A RESIDENT MEMBER".
    # The 97 children at Montachusett Regional Vocational Technical are Resident/Member
    # rows -- of Monty Tech, a district Lunenburg belongs to and does not run. Subtracting
    # the Resident/Member reason instead of the Lunenburg LEA hid the largest single
    # destination in the file, and would have published 80 where the measured figure is
    # 177.
    by_reason = collections.defaultdict(lambda: collections.defaultdict(float))
    here = collections.defaultdict(float)
    away = collections.defaultdict(lambda: collections.defaultdict(float))
    for fy, reason, dist, lea, n in rows:
        by_reason[fy][reason] += n or 0
        if lea == LEA:
            here[fy] += n or 0
        else:
            away[fy][dist] += n or 0
    reasons = sorted({r[1] for r in rows})
    series = []
    for fy in years:
        tot = sum(by_reason[fy].values())
        series.append({
            'fy': fy, 'total': int(tot), 'in_lunenburg': int(here[fy]),
            'elsewhere': int(tot - here[fy]),
            'elsewhere_pct': round(100.0 * (tot - here[fy]) / tot, 2),
            **{r: int(by_reason[fy].get(r, 0)) for r in reasons}})
    if not here:
        fail('not one resident child is recorded as enrolled in the Lunenburg district')

    # Where the school-choice children actually go, latest year and the whole record.
    dest = collections.defaultdict(list)
    for fy, reason, dist, _lea, n in rows:
        if reason == 'School Choice Program':
            dest[fy].append({'district': dist, 'students': int(n or 0)})
    if not dest:
        fail('no school choice rows for %s -- refusing to publish a page about a '
             'programme with no measured rows' % TOWN)
    latest = max(dest)
    destinations = sorted(dest[latest], key=lambda d: (-d['students'], d['district']))
    # Which destinations appear in every year of the record, and which are one-offs.
    appears = collections.Counter()
    for fy in dest:
        for d in dest[fy]:
            appears[d['district']] += 1
    persistent = sorted(({'district': k, 'years': v, 'of': len(dest)}
                         for k, v in appears.items()),
                        key=lambda r: (-r['years'], r['district']))

    # EVERY district that educates a Lunenburg child in the latest year, whatever the
    # reason -- which is what a resident actually asks, and which school choice alone
    # answers only in part.
    elsewhere_latest = sorted(
        ({'district': k, 'students': int(v)} for k, v in away[max(years)].items()),
        key=lambda r: (-r['students'], r['district']))
    if not elsewhere_latest:
        fail('no district outside Lunenburg educates a resident child in the latest '
             'year -- refusing to publish that')

    # THE OTHER DIRECTION, from the same file: children who arrive in Lunenburg.
    incoming = q(db, """
        SELECT fy, SUM(students) FROM dese_town_enrollment
        WHERE lea=? AND town <> ? AND enrollment_reason='School Choice Program'
        GROUP BY fy ORDER BY fy""", LEA, TOWN)
    inbound = [{'fy': fy, 'students': int(n or 0)} for fy, n in incoming]
    net = []
    inb = {r['fy']: r['students'] for r in inbound}
    for s in series:
        if s['fy'] in inb:
            out = s.get('School Choice Program', 0)
            net.append({'fy': s['fy'], 'out': out, 'in': inb[s['fy']],
                        'net': inb[s['fy']] - out})
    if not net:
        fail('the inbound and outbound school choice series share no year')

    # -------------------------------------------------------------- THE THREE ROUTES
    #
    # THIS IS THE FINDING, and it is invisible in the total. `elsewhere` moves 186 -> 177
    # across thirteen years while the three routes underneath it move +38.6%, -15.9% and
    # -50.0%. Anybody watching only the total would report that nothing is happening.
    #
    # THEY ARE THREE DIFFERENT LEGAL MECHANISMS AND THE PAGE NEVER SUMS THEM WITHOUT
    # SAYING SO:
    #
    #   * MONTY TECH IS NOT CHOOSING OUT. Lunenburg is a MEMBER TOWN of the Montachusett
    #     Regional Vocational Technical district, so those children are Resident/Member
    #     rows -- of Monty Tech. The town is assessed for them whether or not it likes the
    #     figure, and no Lunenburg decision admits or refuses any of them.
    #   * SCHOOL CHOICE is a family applying to a district that has opened seats. The
    #     sending town pays tuition off its cherry sheet.
    #   * CHARTER is a family applying to a charter school -- a different statute and a
    #     different flow of money.
    #
    # KEYED ON THE LEA CODE, NOT ON THE DISTRICT NAME. Rule 13: a name is a rendering and
    # DESE has renamed districts inside this file's own span. 08320000 does not move.
    monty_rows = [r for r in rows if r[3] == MONTY]
    if not monty_rows:
        fail('no rows for LEA %s (Montachusett Regional Vocational Technical). A join '
             'that matches nothing looks exactly like a town with no vocational students'
             % MONTY)
    monty = collections.defaultdict(float)
    for fy, _reason, _dist, lea, n in monty_rows:
        monty[fy] += n or 0

    routes = []
    for s_ in series:
        fy = s_['fy']
        m = int(monty[fy])
        ch = s_.get('School Choice Program', 0)
        ct = s_.get('Charter School', 0)
        other = s_['elsewhere'] - m - ch - ct
        # A negative residual would mean a school-choice or charter row carried the
        # Lunenburg LEA, which would make `elsewhere` and the reason columns count
        # different things. Refuse rather than publish a decomposition that does not sum.
        if other < 0:
            fail('FY%d: the three routes (%d + %d + %d) exceed the %d children educated '
                 'outside Lunenburg' % (fy, m, ch, ct, s_['elsewhere']))
        routes.append({'fy': fy, 'monty_tech': m, 'school_choice': ch, 'charter': ct,
                       'other': other, 'elsewhere': s_['elsewhere'],
                       'in_lunenburg': s_['in_lunenburg']})

    def pct(a, b):
        return round(100.0 * (b - a) / a, 1) if a else None

    rf, rl = routes[0], routes[-1]
    route_change = {k: {'first': rf[k], 'last': rl[k], 'pct': pct(rf[k], rl[k])}
                    for k in ('monty_tech', 'school_choice', 'charter', 'elsewhere',
                              'in_lunenburg')}

    first, last = series[0], series[-1]
    peak = max(series, key=lambda s: s.get('School Choice Program', 0))
    rc = route_change
    biggest_dest = elsewhere_latest[0]
    return {
        'about': 'Where Lunenburg’s resident children actually go to school, from '
                 'DESE’s count of residents by district — every reason, both '
                 'directions, SY2014 onward.',
        'grain': 'A count of children by town-and-district pair. THE FILE CARRIES NO '
                 'DISABILITY FLAG, so nothing on this page is a special education figure.',
        'sources': [
            doc(mf, 'state-dese/dese-residents-sending.xlsx', 'dese_town_enrollment', DESE,
                'Enrollment of town residents by district (vxt3-k35x). Where each '
                'town’s children are enrolled, and under which programme.'),
            doc(mf, 'state-dese/dese-enrollment-receiving.xlsx', 'dese_town_enrollment',
                DESE,
                'The companion file (8xyg-59b2): who arrives at a district, and from '
                'where. Row for row it holds the identical rows and differs only in '
                'column order.'),
        ],
        'fy_first': first['fy'], 'fy_last': last['fy'],
        'reasons': reasons,
        'series': series,
        'first': first, 'last': last, 'peak_choice_year': peak['fy'],
        'peak_choice': peak.get('School Choice Program', 0),
        'latest_year': latest,
        'destinations': destinations,
        'destination_count': len(destinations),
        'persistent': persistent,
        'elsewhere_latest': elsewhere_latest,
        'inbound': inbound,
        'net': net,
        'routes': routes,
        'route_change': route_change,
        'three_routes': [
            {'route': 'Montachusett Regional (Monty Tech)',
             'key': 'monty_tech',
             'what': 'NOT choosing out. Lunenburg is a MEMBER TOWN of the regional '
                     'vocational district, so these children are reported as '
                     'Resident/Member — of Monty Tech. The town is assessed for them, '
                     'and no Lunenburg decision admits or refuses any of them.'},
            {'route': 'School choice',
             'key': 'school_choice',
             'what': 'A family applies to another district that has opened seats. The '
                     'sending town pays tuition, taken off its cherry sheet. The '
                     'receiving district decides how many seats to open; the sending '
                     'town decides nothing.'},
            {'route': 'Charter schools',
             'key': 'charter',
             'what': 'A family applies to a charter school. A different statute and a '
                     'different flow of money from school choice, assessed on the town '
                     'separately.'},
        ],
        'conclusions': emit('where-students-go-instead', [
            conclusion(
                id='the-total-held-while-its-parts-changed',
                claim='Change in children schooled outside Lunenburg, over %s years'
                      % C.num(len(series)),
                so_what='The total barely moved. Where they go changed completely, and the '
                        'routes cost the town different amounts.',
                lede='The number of Lunenburg children going to school somewhere other '
                      'than a Lunenburg school has barely moved in %s years \u2014 %s '
                      'then, %s now, a change of %s \u2014 while where they go changed '
                      'completely.'
                      % (C.num(len(series)), C.num(rc['elsewhere']['first']),
                         C.num(rc['elsewhere']['last']),
                         C.pct(rc['elsewhere']['pct'])),
                detail='Monty Tech went %s to %s. School choice went %s to %s. Charter '
                       'schools went %s to %s. Anybody watching only the total would '
                       'report that nothing is happening here, and three things beneath it '
                       'are moving in different directions at once, one of them by half. '
                       'Over the same span the children in Lunenburg\u2019s own schools '
                       'went %s to %s. That matters for planning because the three routes '
                       'cost the town different amounts and none of them is controlled by '
                       'the same decision.'
                       % (C.num(rc['monty_tech']['first']), C.num(rc['monty_tech']['last']),
                          C.num(rc['school_choice']['first']),
                          C.num(rc['school_choice']['last']),
                          C.num(rc['charter']['first']), C.num(rc['charter']['last']),
                          C.num(rc['in_lunenburg']['first']),
                          C.num(rc['in_lunenburg']['last'])),
                figure='total_change',
                figures={
                    'total_change': figure(rc['elsewhere']['pct'],
                                           C.pct(rc['elsewhere']['pct'])),
                    'years': figure(len(series), C.num(len(series)), 'years'),
                    'elsewhere_from': figure(rc['elsewhere']['first'],
                                             C.num(rc['elsewhere']['first'])),
                    'elsewhere_to': figure(rc['elsewhere']['last'],
                                           C.num(rc['elsewhere']['last'])),
                    'monty_from': figure(rc['monty_tech']['first'],
                                         C.num(rc['monty_tech']['first'])),
                    'monty_to': figure(rc['monty_tech']['last'],
                                       C.num(rc['monty_tech']['last'])),
                    'choice_from': figure(rc['school_choice']['first'],
                                          C.num(rc['school_choice']['first'])),
                    'choice_to': figure(rc['school_choice']['last'],
                                        C.num(rc['school_choice']['last'])),
                    'charter_from': figure(rc['charter']['first'],
                                           C.num(rc['charter']['first'])),
                    'charter_to': figure(rc['charter']['last'],
                                         C.num(rc['charter']['last'])),
                    'here_from': figure(rc['in_lunenburg']['first'],
                                        C.num(rc['in_lunenburg']['first'])),
                    'here_to': figure(rc['in_lunenburg']['last'],
                                      C.num(rc['in_lunenburg']['last'])),
                },
                kind='measured',
                basis='DESE\u2019s count of resident children by town and district, every '
                      'reason and both directions, for every year it has been published.',
                not_shown='Why any family left. A count of departures is not a reason for '
                          'them, and nothing in this file or in the meeting record surveys '
                          'the households.',
                see=[('/monty-tech', 'what Monty Tech is assessed for'),
                     ('/if-students-leave', 'what more leaving would cost')],
            ),
            conclusion(
                id='the-biggest-destination-is-not-school-choice',
                claim='Lunenburg children at Monty Tech, the largest single destination',
                so_what='More than school choice and charter together. Lunenburg is a '
                        'member town there, so this is not choosing out.',
                lede='The largest single destination for a Lunenburg child educated '
                      'elsewhere is not school choice. It is %s, with %s children.'
                      % (biggest_dest['district'], C.num(biggest_dest['students'])),
                detail='More than school choice and charter schools put together. Those '
                       'children are counted as resident MEMBERS, because Lunenburg belongs '
                       'to that district and helps fund it \u2014 a family choosing it is '
                       'not choosing OUT of anything the town runs, and no Lunenburg '
                       'decision admits or refuses any of them. Reading '
                       '\u201cchildren who leave\u201d as school choice alone understates '
                       'the count by more than half and points the argument at the one '
                       'route the town has least to do with.',
                figures={
                    'students': figure(biggest_dest['students'],
                                       C.num(biggest_dest['students']), 'children'),
                },
                figure='students',
                kind='measured',
                basis='DESE\u2019s resident-by-district count for the latest published '
                      'year, read by district rather than by enrollment reason.',
                not_shown='What any of it costs. The archive holds the counts and not one '
                          'document stating the tuition Lunenburg is assessed for these '
                          'children by route.',
                see=[('/monty-tech', 'the Monty Tech assessment')],
            ),
        ]),
        'said': said_for('leaving'),
        'searched': searched('leaving'),
        'minutes': coverage(),
        'not_established': [
            'THAT ANY OF THESE CHILDREN HAS AN IEP. This is the one that matters, and it '
            'is why this report is separate from the other three. DESE publishes the '
            'count by town, district and programme and does not publish disability '
            'status with it. A special education student who leaves under school choice '
            'and a student with no IEP who leaves are one row here.',
            'What any of it costs. The archive holds the counts and not one document '
            'stating the tuition Lunenburg is assessed for them — already registered '
            'in `money-gaps.csv` on both the money-out and the people side.',
            'WHICH GRADES they leave in — the question everybody actually asks. '
            'dese_town_enrollment carries no grade column, and the grade counts that do '
            'exist are headcounts INSIDE a district rather than an outflow from a town, '
            'so they cannot be differenced to recover it. Whether families leave at a '
            'transition year or steadily throughout is unknown, and those imply '
            'completely different things about what the district could change. '
            'Registered in `money-gaps.csv` as “Which grades Lunenburg children leave '
            'the district in”.',
            'Why any family left. A count of departures is not a reason for them, and '
            'nothing in this file or in the meeting record surveys the households.',
            'That a child leaving is a child the district no longer spends on. Out-of-'
            'district special education placements are NOT in this file: a placed child '
            'stays enrolled in Lunenburg and is counted as a resident member.',
        ],
        'closes': 'DLS Cherry Sheet CS 1-EB (estimated charges) for Lunenburg, which '
                  'prints the school choice sending and charter tuition assessments on '
                  'their own lines — the money. For the disability question, '
                  'DESE’s SIMS detail crossing enrollment reason with IEP status, '
                  'which is not published at town level at all.',
    }


# =====================================================================================
# 3. WHAT IT COSTS, AND WHAT CIRCUIT BREAKER REIMBURSES
# =====================================================================================

def build_cost(db, mf):
    """Out-of-district tuition by FUND, and the reimbursement that is not in the budget."""
    # THE ONLY SPECIAL EDUCATION SPENDING DESE'S RETURN IDENTIFIES AS SUCH.
    tuition = q(db, """
        SELECT fy, func_code, func_desc, gen_fund, grants_revolving, total
        FROM dese_function_expenditure
        WHERE lea=? AND level='detail' AND func_code IN ('9300','9400')
        ORDER BY fy, func_code""", LEA)
    if not tuition:
        fail('the out-of-district tuition join matched nothing')
    fund = collections.defaultdict(lambda: {'gen_fund': 0.0, 'grants': 0.0, 'total': 0.0})
    per_code = collections.defaultdict(dict)
    for fy, code, _d, g, gr, t in tuition:
        fund[fy]['gen_fund'] += g or 0
        fund[fy]['grants'] += gr or 0
        fund[fy]['total'] += t or 0
        per_code[fy][code] = {'gen_fund': round(g or 0), 'grants': round(gr or 0),
                              'total': round(t or 0)}
    spend = [{'fy': fy, 'gen_fund': round(v['gen_fund']), 'grants': round(v['grants']),
              'total': round(v['total']),
              'outside_share_pct': round(100.0 * v['grants'] / v['total'], 2)
              if v['total'] else 0.0,
              'ratio': round(v['total'] / v['gen_fund'], 3) if v['gen_fund'] else None}
             for fy, v in sorted(fund.items())]
    need(spend, 'cost', 'the out-of-district tuition years')

    # THE IDENTITY THAT ESTABLISHES WHAT THE BUDGET LINE IS. The district's own restated
    # budget figures for the same two lines are compared, year by year, to DESE's GENERAL
    # FUND column and to DESE's ALL-FUNDS column. Which of the two it matches is the
    # answer to "is the budget line net or gross of the reimbursement" -- and it is
    # measured here rather than assumed.
    hist = q(db, """
        SELECT fy, private, collaborative, total FROM ood_tuition_history
        WHERE stage='restated' ORDER BY fy""")
    if not hist:
        fail('the restated out-of-district budget rows matched nothing')
    match = []
    byfy = {s['fy']: s for s in spend}
    for fy, priv, coll, tot in hist:
        s = byfy.get(fy)
        if not s:
            continue
        match.append({'fy': fy, 'budget': int(tot), 'dese_gen_fund': s['gen_fund'],
                      'dese_all_funds': s['total'],
                      'vs_gen_fund': int(tot) - s['gen_fund'],
                      'vs_all_funds': int(tot) - s['total'],
                      'ties_gen_fund': abs(int(tot) - s['gen_fund']) <= 2})
    if len(match) < 8:
        fail('only %d years compare the district budget line to DESE by fund' % len(match))
    ties = [m for m in match if m['ties_gen_fund']]
    misses = [m for m in match if not m['ties_gen_fund']]
    if not ties:
        fail('the district’s restated out-of-district budget line no longer ties to '
             'DESE’s general fund column in ANY year -- the identity this page rests '
             'on has moved and the prose about it would be wrong')

    # CIRCUIT BREAKER, from DESE's own reimbursement file. `level='district'` explicitly:
    # the same file carries a State row.
    cb = need(q(db, """
        SELECT fy, eligible_students_claimed, total_eligible_expenses, threshold_amount,
               total_net_claim, reimb_instruction_tuition, reimb_transport,
               total_quarterly_payment, extra_relief_payment,
               additional_supplemental_payment, comments
        FROM dese_circuit_breaker WHERE lea=? AND level='district' ORDER BY fy""", LEA),
        'cb', 'the circuit breaker rows')
    breaker = []
    for (fy, students, elig, thresh, claim, rt, rtr, paid, relief, supp, note) in cb:
        breaker.append({
            'fy': fy, 'students': int(students or 0), 'eligible': round(elig or 0),
            'threshold': round(thresh or 0), 'net_claim': round(claim or 0),
            'reimb_tuition': round(rt or 0), 'reimb_transport': round(rtr or 0),
            'paid': round(paid or 0), 'extra_relief': round(relief or 0),
            'supplemental': round(supp or 0),
            'paid_share_of_eligible': round(100.0 * (paid or 0) / elig, 2) if elig else 0.0,
            # THE MECHANISM, computed rather than described. The file prints an eligible
            # expense, a threshold and a net claim, and in most years the first minus the
            # second is exactly the third -- so the threshold is a deduction and not a
            # rate. It is NOT exact in every year, and the residual is published rather
            # than rounded away.
            'claim_residual': round((elig or 0) - (thresh or 0) - (claim or 0)),
            'threshold_per_student': round((thresh or 0) / students) if students else None,
            'comment': note or ''})
    cb_first, cb_last = breaker[0], breaker[-1]
    cb_identity = [b['fy'] for b in breaker if b['claim_residual'] == 0]
    cb_identity_breaks = [b['fy'] for b in breaker if b['claim_residual'] != 0]
    cb_peak_students = max(breaker, key=lambda b: b['students'])
    cb_low_students = min(breaker, key=lambda b: b['students'])
    transport_years = [b for b in breaker if b['reimb_transport']]

    # A COMPARISON THAT IS NOT AN ATTRIBUTION. The money outside the appropriation and the
    # reimbursement received are both real and are not the same series; they are published
    # side by side with the difference stated, and never differenced into a claim.
    beside = []
    cbfy = {b['fy']: b for b in breaker}
    for s in spend:
        b = cbfy.get(s['fy'])
        if b:
            beside.append({'fy': s['fy'], 'outside_appropriation': s['grants'],
                           'circuit_breaker_paid': b['paid'],
                           'difference': s['grants'] - b['paid']})
    if not beside:
        fail('the tuition and circuit breaker series share no year')

    last = spend[-1]
    widest = max((s for s in spend if s['ratio']), key=lambda s: s['ratio'])
    # THE SHAPE OF THE SERIES, not just its ends. Residents describe this line as rising
    # relentlessly; measured across all funds it peaked years ago and has moved in both
    # directions since, which is a different fact about the world and the one worth saying.
    peak = max(spend, key=lambda s: s['total'])
    low = min(spend, key=lambda s: s['total'])
    down_from_peak = round(100.0 * (peak['total'] - last['total']) / peak['total'], 1)
    most_outside = max(spend, key=lambda s: s['outside_share_pct'])
    least_outside = min(spend, key=lambda s: s['outside_share_pct'])
    return {
        'about': 'What Lunenburg spends on out-of-district special education placement, '
                 'split by the fund that paid it — and what the state reimburses '
                 'through the circuit breaker.',
        'grain': 'Dollars. Closed-year spending from a statutory return, and a state '
                 'payment schedule. Not students, and not the appropriation the town votes.',
        'sources': [
            doc(mf, 'state-dese/district-expenditures-by-function.xlsx',
                'dese_function_expenditure', DESE,
                'End of Year Financial Report. Every dollar of district spending '
                'attributed to the general fund or to grants and revolving funds, by '
                'function code.'),
            doc(mf, 'state-dese/dese-circuit-breaker.xlsx', 'dese_circuit_breaker', DESE,
                'The circuit breaker reimbursement schedule: claimed students, eligible '
                'expenses, the threshold, and what was actually paid.'),
        ],
        'fy_first': spend[0]['fy'], 'fy_last': last['fy'],
        'spend': spend,
        'per_code': [{'fy': fy, **{k: v for k, v in codes.items()}}
                     for fy, codes in sorted(per_code.items())],
        'last': last, 'widest': widest,
        'budget_vs_fund': match,
        'ties_years': [m['fy'] for m in ties],
        'miss_years': [m['fy'] for m in misses],
        'ties_count': len(ties), 'compared_count': len(match),
        'breaker': breaker,
        'cb_first': cb_first, 'cb_last': cb_last,
        'cb_peak_students': cb_peak_students, 'cb_low_students': cb_low_students,
        'cb_transport_first_year': transport_years[0]['fy'] if transport_years else None,
        'cb_identity_years': cb_identity,
        'cb_identity_breaks': cb_identity_breaks,
        'beside': beside,
        # WHAT A RESIDENT SHOULD TAKE AWAY, computed here rather than written on the
        # page. Everyone in this town says special education is expensive and rising;
        # these say what is actually happening to that money. Rule 8: what it means for
        # planning, never what anybody got wrong.
        'conclusions': emit('what-special-education-costs', [
            conclusion(
                id='the-line-is-the-towns-share',
                claim='Of what Lunenburg spent teaching children at other schools was '
                      'paid from outside the budget',
                so_what='The figure residents argue about is the town\u2019s share of '
                        'that bill, not the bill.',
                lede='The special education figure residents argue about \u2014 what the '
                      'schools pay other schools to teach children Lunenburg cannot \u2014 '
                      'is the town\u2019s share of that bill and not the bill. In %s the '
                      'budget said %s and %s was spent.'
                      % (C.fy(last['fy']), C.usd(last['gen_fund']), C.usd(last['total'])),
                detail='The district\u2019s own restated budget figure equals DESE\u2019s '
                       'general fund column, to within a dollar or two, in %s of the %s '
                       'years the two can be compared \u2014 and equals the all-funds '
                       'column in none of them. So %s, %s of what was spent on '
                       'out-of-district placement that year, was paid from funds that '
                       'never appear in the appropriation at all. A resident watching the '
                       'budget line is watching what the town raises, which can move '
                       'without a single placement changing.'
                       % (C.num(len(ties)), C.num(len(match)), C.usd(last['grants']),
                          C.pct(last['outside_share_pct'])),
                figures={
                    'fy': figure(last['fy'], C.fy(last['fy'])),
                    'budget_line': figure(last['gen_fund'], C.usd(last['gen_fund'])),
                    'all_funds': figure(last['total'], C.usd(last['total'])),
                    'ties': figure(len(ties), C.num(len(ties))),
                    'compared': figure(len(match), C.num(len(match))),
                    'outside': figure(last['grants'], C.usd(last['grants'])),
                    'outside_share': figure(last['outside_share_pct'],
                                            C.pct(last['outside_share_pct'])),
                },
                figure='outside_share',
                kind='measured',
                basis='DESE\u2019s End of Year Financial Report, functions 9300 and 9400, '
                      'against the district\u2019s own restated budget book, year by year.',
                not_shown='Which fund paid the rest. DESE reports one grants-and-revolving '
                          'total and names no fund, so the money outside the appropriation '
                          'cannot be attributed to the circuit breaker, to a grant, or to '
                          'anything else.',
                see=[('/money-outside-the-budget', 'the money outside the budget'),
                     ('/when-grants-end', 'what happens when a grant stops')],
            ),
            conclusion(
                id='the-threshold-comes-off-first',
                claim='Taken off the bill in %s before the state reimburses anything'
                      % C.fy(cb_last['fy']),
                so_what='So the town carries the first slice of these placements in every '
                        'year, whatever else happens.',
                lede='The state does reimburse out-of-district tuition, but it takes a '
                      'threshold off before it pays anything \u2014 in %s that threshold '
                      'was %s.' % (C.fy(cb_last['fy']), C.usd(cb_last['threshold'])),
                detail='Lunenburg claimed %s of eligible expense and was paid %s, which is '
                       '%s of the claim. That the threshold is a deduction rather than a '
                       'rate is measured and not described: eligible expense minus '
                       'threshold equals the net claim exactly in %s of the %s years the '
                       'state has published. So the reimbursement grows as costs grow and '
                       'never reaches the first slice of them, and the town carries that '
                       'slice in every year whatever else happens.'
                       % (C.usd(cb_last['eligible']), C.usd(cb_last['paid']),
                          C.pct(cb_last['paid_share_of_eligible']),
                          C.num(len(cb_identity)), C.num(len(breaker))),
                figures={
                    'fy': figure(cb_last['fy'], C.fy(cb_last['fy'])),
                    'threshold': figure(cb_last['threshold'], C.usd(cb_last['threshold'])),
                    'eligible': figure(cb_last['eligible'], C.usd(cb_last['eligible'])),
                    'paid': figure(cb_last['paid'], C.usd(cb_last['paid'])),
                    'paid_share': figure(cb_last['paid_share_of_eligible'],
                                         C.pct(cb_last['paid_share_of_eligible'])),
                    'identity_years': figure(len(cb_identity), C.num(len(cb_identity))),
                    'years': figure(len(breaker), C.num(len(breaker))),
                },
                figure='threshold',
                kind='measured',
                basis='DESE\u2019s circuit breaker reimbursement schedule: claimed '
                      'students, eligible expense, the threshold, the net claim and what '
                      'was actually paid, every year it has been published.',
                not_shown='What the receipt was spent on. The reimbursement lands in a '
                          'revolving fund that carries a balance forward, so a payment '
                          'received in one year is not established to have paid for that '
                          'year\u2019s placements.',
            ),
            conclusion(
                id='out-of-district-spending-is-not-a-straight-line',
                claim='Spent teaching children at other schools in %s' % C.fy(last['fy']),
                so_what='It peaked at %s in %s. This cost steps with single placements '
                        'rather than rising steadily.'
                        % (C.usd(peak['total']), C.fy(peak['fy'])),
                lede='Out-of-district tuition has not risen relentlessly. Measured across '
                      'every fund it peaked at %s in %s, and %s came in at %s.'
                      % (C.usd(peak['total']), C.fy(peak['fy']), C.fy(last['fy']),
                         C.usd(last['total'])),
                detail='That is %s below the peak, and the series moves in both '
                       'directions across the %s years it covers \u2014 a low of %s and a '
                       'high of %s. What moves further than the total is who pays it: the '
                       'share falling outside the appropriation has been as high as %s and '
                       'as low as %s, so the line the town votes can rise in a year when '
                       'spending falls. Out-of-district placement is a small number of '
                       'children and the state\u2019s own reimbursement threshold for %s '
                       'was %s per child, so one family moving in or out moves this series '
                       'more than any policy does. A single year of it means very little.'
                       % (C.pct(down_from_peak), C.num(len(spend)), C.usd(low['total']),
                          C.usd(peak['total']), C.pct(most_outside['outside_share_pct']),
                          C.pct(least_outside['outside_share_pct']),
                          C.fy(cb_last['fy']), C.usd(cb_last['threshold_per_student'])),
                figures={
                    'peak': figure(peak['total'], C.usd(peak['total'])),
                    'peak_fy': figure(peak['fy'], C.fy(peak['fy'])),
                    'last_fy': figure(last['fy'], C.fy(last['fy'])),
                    'last_total': figure(last['total'], C.usd(last['total'])),
                    'down_from_peak': figure(down_from_peak, C.pct(down_from_peak)),
                    'years': figure(len(spend), C.num(len(spend))),
                    'low': figure(low['total'], C.usd(low['total'])),
                    'most_outside': figure(most_outside['outside_share_pct'],
                                           C.pct(most_outside['outside_share_pct'])),
                    'least_outside': figure(least_outside['outside_share_pct'],
                                            C.pct(least_outside['outside_share_pct'])),
                    'cb_fy': figure(cb_last['fy'], C.fy(cb_last['fy'])),
                    'threshold_per_child': figure(cb_last['threshold_per_student'],
                                                  C.usd(cb_last['threshold_per_student'])),
                },
                figure='last_total',
                kind='measured',
                basis='DESE\u2019s End of Year Financial Report, all funds, functions '
                      '9300 and 9400, every year it has been published.',
                not_shown='That the need fell. A placement count and a placement cost are '
                          'different quantities: a year with fewer dollars may be a year '
                          'with fewer children, with cheaper placements, or with more of '
                          'the cost carried by a fund that is not the appropriation.',
                see=[('/who-ends-up-out-of-district', 'the placement count itself')],
            ),
        ]),
        'said': said_for('cost'),
        'searched': searched('cost'),
        'minutes': coverage(),
        'not_established': [
            'What special education costs in district. DESE’s function codes carry '
            'no special education category at all: 9300 and 9400 are the only two on the '
            'whole return that name it, and both are tuition paid to somebody else. '
            'Every in-district figure this project holds rests on a classification '
            'somebody made, and that one is ours — see /bend-the-curve.',
            'That the money outside the appropriation IS the circuit breaker. Both series '
            'are published above and the difference between them is stated. The grants '
            'and revolving column holds every non-general fund together, and the circuit '
            'breaker account carries a balance forward, so the two would not equal each '
            'other even if one paid the whole of the other.',
            'What any single placement costs. No document in this archive prices one, '
            'and nothing here divides a tuition total by a placement count — the two '
            'come from different returns with different inclusion rules.',
            'That a falling tuition line is a cheaper year. Rule 11: the line is net, and '
            'a year when more of it was paid from the reimbursement account looks '
            'identical on the expense side to a year when fewer children were placed.',
        ],
        'closes': 'The district’s circuit breaker revolving fund cashbook for the '
                  'year, which shows what the receipt was actually spent on — '
                  'already the named remedy in `money-gaps.csv`. For the in-district '
                  'question, Schedule 19 of the End of Year Financial Report as filed, '
                  'which lists each grant and revolving fund separately.',
    }


# =====================================================================================
# 4. THE ROUTE INTO OUT-OF-DISTRICT PLACEMENT
# =====================================================================================

def build_route(db, mf):
    """Where a placement leads -- a cohort, and the town's own count, kept apart."""
    traj = need(q(db, """
        SELECT fy, grade_span, placement_at_start, cohort_cnt, no_iep_cnt, included_cnt,
               sub_separate_cnt, out_of_district_cnt, unaccounted_cnt, reconciles
        FROM dese_sped_trajectory WHERE lea=? AND geo_level='district'
        ORDER BY fy, grade_span, placement_at_start""", LEA),
        'route', 'the placement trajectory rows')
    cohorts = []
    for (fy, span, start, tot, noiep, incl, sub, ood, left, rec) in traj:
        if tot is None or ood is None:
            continue
        cohorts.append({
            'fy': fy, 'grade_span': span, 'start': start, 'cohort': int(tot),
            'no_iep': int(noiep or 0), 'included': int(incl or 0),
            'sub_separate': int(sub or 0), 'out_of_district': int(ood or 0),
            'unaccounted': int(left or 0), 'reconciles': rec == 'yes',
            'ood_pct': round(100.0 * ood / tot, 1) if tot else 0.0})
    k12 = [c for c in cohorts if c['grade_span'] == 'K-12']
    if not k12:
        fail('no K-12 trajectory cohort for Lunenburg')

    # THE COMPARISON THE PAGE IS FOR, and the reason the bases travel with it: 14.3% of 28
    # is four children.
    starts = sorted({c['start'] for c in k12})
    if len(starts) < 2:
        fail('only one starting placement in the trajectory -- there is no route to compare')
    pooled = {}
    for s in starts:
        rows = [c for c in k12 if c['start'] == s]
        coh = sum(c['cohort'] for c in rows)
        ood = sum(c['out_of_district'] for c in rows)
        pooled[s] = {'start': s, 'years': len(rows), 'cohort': coh, 'out_of_district': ood,
                     'ood_pct': round(100.0 * ood / coh, 1) if coh else 0.0}

    # THE STATE, AS A BENCHMARK ONLY. Queried by geo_level='state' explicitly and never
    # added to anything -- this is the rollup that once turned a $26.6M district into $116M.
    st = q(db, """
        SELECT fy, placement_at_start, cohort_cnt, out_of_district_cnt
        FROM dese_sped_trajectory WHERE geo_level='state' AND grade_span='K-12'
        ORDER BY fy, placement_at_start""")
    if not st:
        fail('the state benchmark join matched nothing')
    state = [{'fy': fy, 'start': s, 'cohort': int(c), 'out_of_district': int(o),
              'ood_pct': round(100.0 * o / c, 1)} for fy, s, c, o in st if c]
    latest_fy = max(c['fy'] for c in k12)
    latest = [c for c in k12 if c['fy'] == latest_fy]
    latest_state = [s for s in state if s['fy'] == latest_fy]

    # THE TOWN'S OWN COUNT, from the Special Services report in each annual town report.
    # A DIFFERENT INSTRUMENT: measured on 1 March, sourced to SIMS Report 7, and split
    # into collaborative, day and residential. It is NOT joined to anything above.
    place = need(q(db, """
        SELECT fy, as_of, total, collaborative, day, residential, collaborative_basis,
               parts_tie, chain_agrees, page, document
        FROM placement_counts ORDER BY fy"""),
        'place', 'the published placement counts')
    counts = [{'fy': fy, 'as_of': a, 'total': int(t) if str(t).strip() else None,
               'collaborative': int(c) if str(c).strip() else None,
               'day': int(d) if str(d).strip() else None,
               'residential': int(r) if str(r).strip() else None,
               'collaborative_basis': cb or '',
               'parts_tie': pt == 'yes', 'chain_agrees': ca == 'yes',
               'page': pg, 'document': dc}
              for fy, a, t, c, d, r, cb, pt, ca, pg, dc in place]
    # TWO DIFFERENT KINDS OF HOLE, and conflating them would misdescribe both. In one year
    # the report prints a total and no split at all; in the earliest years it prints a
    # split on a DIFFERENT BASIS -- collaborative placements counted inside the day figure
    # rather than beside it -- so the parts are complete and are not comparable with the
    # later ones. The CSV records which, in `collaborative_basis`, and it is read here
    # rather than inferred from an empty cell.
    no_split = [c['fy'] for c in counts
                if c['day'] is None and c['residential'] is None
                and c['collaborative'] is None]
    other_basis = sorted({c['collaborative_basis'] for c in counts
                          if c['collaborative_basis']
                          and c['collaborative_basis'] != 'parallel category'})
    other_basis_years = [c['fy'] for c in counts
                         if c['collaborative_basis'] in other_basis]

    # TWO PUBLISHED COUNTS OF THE SAME THING, compared and NOT reconciled.
    dese_ood = dict(q(db, """
        SELECT fy, measure_cnt FROM dese_sped_program
        WHERE lea=? AND geo_level='district'
              AND indicator_category='In District/Out of District'
              AND indicator='Out-of-District'""", LEA))
    if not dese_ood:
        fail('the DESE out-of-district count join matched nothing')
    two = [{'fy': c['fy'], 'town': c['total'], 'dese': int(dese_ood[c['fy']]),
            'difference': int(dese_ood[c['fy']]) - c['total']}
           for c in counts if c['fy'] in dese_ood and c['total'] is not None]
    if not two:
        fail('the town count and the DESE count share no year -- nothing to compare')
    agree = [t for t in two if t['difference'] == 0]
    withtot = [c for c in counts if c['total'] is not None]
    cpeak = max(withtot, key=lambda c: c['total'])
    clow = min(withtot, key=lambda c: c['total'])
    clast = withtot[-1]
    pooled_rows = [pooled[x] for x in starts]
    sub = next(p for p in pooled_rows if p['start'] == 'Substantially Separate Classroom')
    incl = next(p for p in pooled_rows if p['start'] == 'Inclusive Setting')
    lastsub = next(c for c in latest if c['start'] == 'Substantially Separate Classroom')

    return {
        'about': 'The route into out-of-district placement: a cohort followed from where '
                 'it started, and the town’s own published count of children placed.',
        'grain': 'TWO grains, kept apart on purpose. A placement cohort DESE follows, and '
                 'a headcount the town prints on 1 March. Neither is a cost.',
        'sources': [
            doc(mf, 'state-dese/dese-sped-placement-trajectory.xlsx',
                'dese_sped_trajectory', DESE,
                'Special Education Placement Trajectory (92x3-2qj9). Where a cohort '
                'started and where the same children are now. THE BASES ARE TENS OF '
                'CHILDREN.'),
            doc(mf, 'state-dese/dese-sped-program-characteristics.xlsx',
                'dese_sped_program', DESE,
                'Carries DESE’s own count of Lunenburg children placed out of '
                'district, which is a second instrument on the same question.'),
            doc(mf, 'data/placement-counts.csv', 'placement_counts',
                'Lunenburg — read from the annual town reports by this project',
                'The Special Services report in each annual town report, sourced to SIMS '
                'Report 7 and measured on 1 March. Two checks travel with it: the parts '
                'sum to the stated total, and each year states the previous year’s '
                'figure.'),
        ],
        'fy_first': min(c['fy'] for c in k12), 'fy_last': latest_fy,
        'cohorts': cohorts, 'k12': k12, 'starts': starts,
        'pooled': [pooled[s] for s in starts],
        'latest_fy': latest_fy, 'latest': latest,
        'state': state, 'latest_state': latest_state,
        'counts': counts,
        'count_no_split': no_split,
        'count_other_basis': other_basis,
        'count_other_basis_years': other_basis_years,
        'count_first': counts[0], 'count_last': counts[-1],
        'count_peak': max((c for c in counts if c['total'] is not None),
                          key=lambda c: c['total']),
        'count_low': min((c for c in counts if c['total'] is not None),
                         key=lambda c: c['total']),
        'two_counts': two,
        'two_counts_agree': len(agree), 'two_counts_compared': len(two),
        'conclusions': emit('who-ends-up-out-of-district', [
            conclusion(
                id='the-placement-count-fell-and-came-partly-back',
                # "children placed at a school outside the district" reads as SCHOOL
                # CHOICE to anybody who has not already read this page, and this site has
                # a separate report about exactly that. TJ: "this stat is misleading...
                # This is specifically for special education, but reads like school
                # choice." A placement is made because a child's education plan requires
                # it; choosing out is a family applying elsewhere. Two mechanisms, two
                # reports, and the label has to say which one it is.
                claim='Children whose special education plan placed them outside '
                      'Lunenburg schools, %s' % C.fy(clast['fy']),
                so_what='It was %s in %s and %s in %s. The town prints this every year, '
                        'and it moves both ways.'
                        % (C.num(cpeak['total']), C.fy(cpeak['fy']),
                           C.num(clow['total']), C.fy(clow['fy'])),
                lede='The town\u2019s own count of children placed out of district for '
                      'special education ran '
                      'from %s in %s down to %s in %s, and stood at %s in %s.'
                      % (C.num(cpeak['total']), C.fy(cpeak['fy']), C.num(clow['total']),
                         C.fy(clow['fy']), C.num(clast['total']), C.fy(clast['fy'])),
                detail='Lunenburg has printed this figure in the Special Services report of '
                       'every annual town report since %s, sourced to SIMS Report 7 and '
                       'measured on 1 March, split into collaborative, day and residential '
                       'placements. It is the closest thing the town publishes to the '
                       'quantity everybody argues about, and over %s years it has moved in '
                       'both directions rather than only upward. In %s it was %s '
                       'collaborative, %s day and %s residential.'
                       % (C.fy(counts[0]['fy']), C.num(len(counts)), C.fy(clast['fy']),
                          C.num(clast['collaborative']), C.num(clast['day']),
                          C.num(clast['residential'])),
                figures={
                    'peak': figure(cpeak['total'], C.num(cpeak['total'])),
                    'peak_fy': figure(cpeak['fy'], C.fy(cpeak['fy'])),
                    'low': figure(clow['total'], C.num(clow['total'])),
                    'low_fy': figure(clow['fy'], C.fy(clow['fy'])),
                    'last': figure(clast['total'], C.num(clast['total']),
                                   'children placed'),
                    'last_fy': figure(clast['fy'], C.fy(clast['fy'])),
                    'first_fy': figure(counts[0]['fy'], C.fy(counts[0]['fy'])),
                    'years': figure(len(counts), C.num(len(counts))),
                    'collaborative': figure(clast['collaborative'],
                                            C.num(clast['collaborative'])),
                    'day': figure(clast['day'], C.num(clast['day'])),
                    'residential': figure(clast['residential'], C.num(clast['residential'])),
                },
                figure='last',
                allow=('1 March', '7'),
                kind='measured',
                basis='The Special Services report inside each annual town report, page by '
                      'page, with the parts checked against the total the town printed '
                      'beside them.',
                not_shown='What any of it costs. A placement count is children placed; it '
                          'says nothing about which fund paid or what any placement cost, '
                          'and one residential placement can exceed several day '
                          'placements together.',
                see=[('/what-special-education-costs', 'what it costs')],
            ),
            conclusion(
                id='where-a-child-starts-tracks-where-they-end-up',
                claim='Of children starting in a separate special education classroom '
                      'end up outside the district',
                so_what='Against %s of those starting in an ordinary classroom. Small '
                        'groups \u2014 read what this does not show.'
                        % C.pct(incl['ood_pct']),
                lede='Where a child is taught to begin with tracks strongly with whether '
                      'they end up at a school outside Lunenburg: %s of the children who '
                      'started in a separate special education classroom did, against %s '
                      'of those who started in an ordinary one.'
                      % (C.pct(sub['ood_pct']), C.pct(incl['ood_pct'])),
                figure='sub_pct',
                detail='Added up over %s groups the state follows, that is %s children of '
                       '%s against %s of %s. '
                       'The counts are the figure and not the rate: a rate off a base of '
                       '%s moves by %s when one child does. This is the closest the '
                       'published record comes to the question residents ask about early '
                       'intervention, and it is worth having in front of anyone discussing '
                       'in-district capacity \u2014 but see what it does not show, which '
                       'is most of it.'
                       % (C.num(sub['years']), C.num(sub['out_of_district']),
                          C.num(sub['cohort']), C.num(incl['out_of_district']),
                          C.num(incl['cohort']), C.num(lastsub['cohort']),
                          C.points(100.0 / lastsub['cohort'])),
                figures={
                    'sub_pct': figure(sub['ood_pct'], C.pct(sub['ood_pct'])),
                    'incl_pct': figure(incl['ood_pct'], C.pct(incl['ood_pct'])),
                    'cohorts': figure(sub['years'], C.num(sub['years'])),
                    'sub_out': figure(sub['out_of_district'], C.num(sub['out_of_district'])),
                    'sub_base': figure(sub['cohort'], C.num(sub['cohort'])),
                    'incl_out': figure(incl['out_of_district'],
                                       C.num(incl['out_of_district'])),
                    'incl_base': figure(incl['cohort'], C.num(incl['cohort'])),
                    'last_base': figure(lastsub['cohort'], C.num(lastsub['cohort'])),
                    'one_child': figure(100.0 / lastsub['cohort'],
                                        C.points(100.0 / lastsub['cohort'])),
                },
                kind='measured',
                basis='DESE\u2019s special education trajectory file, K-12 rows for '
                      'Lunenburg, pooled across every cohort it publishes.',
                not_shown='That a substantially separate placement LEADS to out of '
                          'district. The children placed in the more intensive setting are '
                          'not a random sample of the others, and selection alone fits '
                          'this exactly. DESE also documents no interval between the '
                          'starting placement and the destination, so every rate here is a '
                          'rate over an unstated span, and the district has told the School '
                          'Committee that some children arrive in Lunenburg already '
                          'requiring a placement, never having been in a cohort at all.',
            ),
        ]),
        'said': said_for('route'),
        'searched': searched('route'),
        'minutes': coverage(),
        'not_established': [
            'Over what period the trajectory measures. DESE publishes the file with no '
            'documentation of the interval between the starting placement and the '
            'destination, and nothing in the workbook states it. Every rate on this page '
            'is therefore a rate over an unstated span.',
            'That a substantially separate placement leads to out-of-district. The '
            'cohorts starting there end out of district far more often than the cohorts '
            'starting in an inclusive setting, and that is a measurement about children '
            'who were already placed differently. Selection alone fits it: the children '
            'placed in the more intensive setting are not a random sample of the others.',
            'That the route runs through the district at all. The district told the '
            'School Committee in February 2026 that children arrive in Lunenburg already '
            'requiring an out-of-district placement. Such a child enters the town’s '
            'count without ever appearing in a cohort followed from an in-district '
            'setting.',
            'Which of the two published counts is right. They agree in some years and not '
            'others, and both are published above rather than averaged. The town counts '
            'on 1 March from SIMS Report 7; DESE publishes its own on its own census, and '
            'nothing states the two dates together.',
            'What any of it costs. A placement count is children placed. It says nothing '
            'about which fund paid or what any placement cost — that is the '
            'companion report, and it is a separate page for this reason.',
        ],
        'closes': 'DESE’s methodology note for dataset 92x3-2qj9, stating the '
                  'interval and the cohort rule; and the district’s own record of '
                  'placements by origin — how many were referred from an in-district '
                  'setting and how many arrived already placed — which nothing in '
                  'this archive publishes.',
    }


# =====================================================================================

def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)
    mf = manifest()
    return {
        'students': build_students(db, mf),
        'leaving': build_leaving(db, mf),
        'cost': build_cost(db, mf),
        'route': build_route(db, mf),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        bad = 0
        for name, payload in data.items():
            out = OUTS[name]
            rel = os.path.relpath(out, ROOT)
            if not os.path.exists(out):
                print('MISSING %s' % rel)
                bad += 1
                continue
            with open(out, encoding='utf-8') as fh:
                have = json.load(fh)
            if have != payload:
                print('STALE %s — run: python3 scripts/build_special_education.py' % rel)
                bad += 1
        if bad:
            return 1
        print('ok — all four special education payloads reproduce from the database')
        return 0

    os.makedirs(PUB, exist_ok=True)
    for name, payload in data.items():
        with open(OUTS[name], 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
            fh.write('\n')
        print('%s' % os.path.relpath(OUTS[name], ROOT))

    s, l, c, r = data['students'], data['leaving'], data['cost'], data['route']
    print('  students: %d on an IEP in FY%d, %.1f%% of enrollment; in+out reconciles in '
          'every year: %s' % (s['last']['swd'], s['last']['fy'], s['last']['share_pct'],
                              s['counts_reconcile']))
    print('  leaving:  %d resident children educated elsewhere in FY%d, %d of them under '
          'school choice, across %d districts'
          % (l['last']['elsewhere'], l['last']['fy'],
             l['last'].get('School Choice Program', 0), l['destination_count']))
    print('  cost:     FY%d out-of-district tuition %s all funds, %s general fund; the '
          'district budget line ties to the general fund column in %d of %d years'
          % (c['last']['fy'], format(c['last']['total'], ','),
             format(c['last']['gen_fund'], ','), c['ties_count'], c['compared_count']))
    print('  route:    %s' % '; '.join(
        '%s %d of %d (%.1f%%)' % (p['start'], p['out_of_district'], p['cohort'],
                                  p['ood_pct']) for p in r['pooled']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
