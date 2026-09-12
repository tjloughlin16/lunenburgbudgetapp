#!/usr/bin/env python3
"""The circuit breaker: what the state has reimbursed Lunenburg for its costliest
special education placements, FY2006 to FY2026, and what it has not.

    python3 scripts/build_circuit_breaker.py            # write fy28/public/data/circuit-breaker.json
    python3 scripts/build_circuit_breaker.py --check    # fail if it no longer reproduces

Page 8 of the build order TJ set on 10 September 2026. `dese_circuit_breaker` was loaded
and unread. /what-special-education-costs already states the FY2026 threshold; this page
owns the twenty-one years, and the three things they show that one year cannot.

THE MECHANISM, because the name explains nothing. For each child whose special education
costs a district more than a THRESHOLD (four times the state average foundation budget
per pupil), the state reimburses a share -- by statute up to 75% -- of the cost ABOVE
the threshold. So the threshold is a DEDUCTION taken off the top per child, and the
share the state actually pays depends on what the Legislature appropriates that year:
when the appropriation is short, every district is pro-rated. Both of those facts are
visible in the numbers and neither is a Lunenburg decision.

THE GRAIN. DESE's own reimbursement file: dollars, per district, per FISCAL year of
PAYMENT, plus a count of the children claimed. `eligible_students_claimed` is CHILDREN.
Reimbursement is paid in the year after the spending it reimburses, so a payment row
answers for the prior year's costs; this page keys everything on the payment year the
file uses and says so.

Rule 7: a count that fell and a cost per child that rose are measurements; why either
moved is not in this file.
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
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'circuit-breaker.json')
DISTRICT = 'Lunenburg'
DOC = dict(key='state-dese/dese-circuit-breaker.xlsx',
           what='Special Education Circuit Breaker reimbursements, every Massachusetts district, FY2006-FY2026: '
                'children claimed, eligible expenses, the threshold, the net claim, and what was paid, by fiscal year of payment.',
           publisher='Massachusetts Department of Elementary and Secondary Education',
           stage='published by the state; dollars paid, and a count of children claimed')


def fail(msg):
    raise SystemExit('build_circuit_breaker: ' + msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def document():
    with open(MANIFEST, encoding='utf-8') as fh:
        rows = {r['key']: r for r in csv.DictReader(fh)}
    r = rows.get(DOC['key'])
    if not r or not r['upstream']:
        fail('%s is not in the manifest with an address (rule 12)' % DOC['key'])
    return [dict(DOC, path='sources/' + DOC['key'], sha256=r['sha256'], bytes=int(r['bytes']), url=r['upstream'],
                 docs_url='/docs/' + DOC['key'], filename=DOC['key'].split('/')[-1], note=DOC['what'] + ' Stage: ' + DOC['stage'])]


def series(db):
    rows = q(db, "SELECT * FROM dese_circuit_breaker WHERE level='district' AND district=? ORDER BY fy", DISTRICT)
    if len(rows) < 15:
        fail('only %d rows for %s' % (len(rows), DISTRICT))
    out = []
    for r in rows:
        kids = r['eligible_students_claimed'] or 0
        elig = r['total_eligible_expenses'] or 0
        thr = r['threshold_amount'] or 0
        claim = r['total_net_claim'] or 0
        paid = r['total_quarterly_payment'] or 0
        if r['reconciles'] == 'no':
            fail('FY%d does not reconcile' % r['fy'])
        out.append(dict(
            fy=r['fy'], children=int(kids), eligible=elig, threshold=thr, claim=claim, paid=paid,
            transport=r['reimb_transport'] or 0, extra=r['extra_relief_payment'] or 0,
            per_child=elig / kids if kids else None,
            threshold_per_child=thr / kids if kids else None,
            paid_share_of_claim=paid / claim if claim else None,
            paid_share_of_eligible=paid / elig if elig else None,
            check=r['reconciles'] or 'no check',
        ))
    return out


def peers(db, fy):
    rows = q(db, "SELECT district, eligible_students_claimed k, total_eligible_expenses e, total_net_claim c, total_quarterly_payment p "
                 "FROM dese_circuit_breaker WHERE level='district' AND fy=? AND eligible_students_claimed > 0 AND district NOT LIKE '%non-op%' ORDER BY district", fy)
    return [dict(district=r['district'], children=int(r['k']), per_child=r['e'] / r['k'], paid_share=r['p'] / r['c'] if r['c'] else None) for r in rows]


def build():
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        s = series(db)
        by = {r['fy']: r for r in s}
        first, last = s[0], s[-1]
        most_kids = max(s, key=lambda r: r['children'])
        fewest = min(s, key=lambda r: r['children'])
        low_share = min((r for r in s if r['paid_share_of_claim']), key=lambda r: r['paid_share_of_claim'])
        high_share = max((r for r in s if r['paid_share_of_claim']), key=lambda r: r['paid_share_of_claim'])
        full_years = sum(1 for r in s if r['paid_share_of_claim'] and r['paid_share_of_claim'] >= 0.70)
        transport_first = next((r for r in s if r['transport']), None)
        transport_peak = max((r for r in s if r['transport']), key=lambda r: r['transport'])
        st = q(db, "SELECT eligible_students_claimed k, total_eligible_expenses e, total_quarterly_payment p FROM dese_circuit_breaker WHERE level='state' AND fy=?", last['fy'])[0]
        pr = peers(db, last['fy'])
        lun_rank = sorted(pr, key=lambda r: -r['per_child']).index(next(r for r in pr if r['district'] == DISTRICT)) + 1

        rows = [
            conclusion(
                id='fewer-children-each-far-more-expensive',
                claim='%s children claimed in FY%d, %s in FY%d; the cost per child went from %s to %s.'
                      % (C.num(most_kids['children']), most_kids['fy'], C.num(last['children']), last['fy'],
                         C.usd(most_kids['per_child']), C.usd(last['per_child'])),
                so_what='A third fewer dollars for a third as many children: each placement costs about twice what one did.',
                figures={'kids_now': figure(last['children'], C.num(last['children']), 'children claimed, FY%d' % last['fy']),
                         'kids_peak': figure(most_kids['children'], C.num(most_kids['children'])),
                         'per_child_then': figure(most_kids['per_child'], C.usd(most_kids['per_child'])),
                         'per_child_now': figure(last['per_child'], C.usd(last['per_child'])),
                         'elig_then': figure(most_kids['eligible'], C.usd(most_kids['eligible'])), 'elig_now': figure(last['eligible'], C.usd(last['eligible'])),
                         'fy_now': figure(last['fy'], 'FY%d' % last['fy']), 'fy_peak': figure(most_kids['fy'], 'FY%d' % most_kids['fy'])},
                figure='kids_now', kind='measured', bearing='sizes',
                lede='The number of children whose placements cost enough to reach the state threshold has fallen by two-thirds; the dollars fell by a third.',
                detail='Eligible expenses were %s for %s children in FY%d and %s for %s in FY%d. The average eligible cost per child claimed roughly doubled '
                       'over those years. A district with nine such placements is exposed to each one: one child arriving or leaving moves this line by more than a tenth.'
                       % (C.usd(most_kids['eligible']), C.num(most_kids['children']), most_kids['fy'], C.usd(last['eligible']), C.num(last['children']), last['fy']),
                basis='`dese_circuit_breaker`, Lunenburg rows, eligible_students_claimed and total_eligible_expenses by fiscal year of payment; per child is the division.',
                not_shown='Which children, which placements, or why the count fell. A claimed child is one whose costs exceeded the threshold; children in '
                          'costly placements below it are not counted here at all.',
                see=[('/what-special-education-costs', 'What out-of-district placements cost'),
                     ('/who-ends-up-out-of-district', 'Who ends up out of district')],
            ),
            conclusion(
                id='the-state-pays-what-it-appropriated',
                claim='The state paid %s of the claim in FY%d and %s in FY%d; the statute allows up to %s.'
                      % (C.pct(100 * low_share['paid_share_of_claim']), low_share['fy'], C.pct(100 * high_share['paid_share_of_claim']), high_share['fy'], '75%'),
                so_what='%s of %s years at %s or more. The share is the Legislature’s appropriation, not Lunenburg’s costs.'
                        % (C.num(full_years), C.num(len(s)), '70%'),
                figures={'low': figure(low_share['paid_share_of_claim'], C.pct(100 * low_share['paid_share_of_claim']), 'of the claim paid, FY%d' % low_share['fy']),
                         'high': figure(high_share['paid_share_of_claim'], C.pct(100 * high_share['paid_share_of_claim'])),
                         'full_years': figure(full_years, C.num(full_years)), 'years': figure(len(s), C.num(len(s))),
                         'fy_low': figure(low_share['fy'], 'FY%d' % low_share['fy']), 'fy_high': figure(high_share['fy'], 'FY%d' % high_share['fy']),
                         'claim_low': figure(low_share['claim'], C.usd(low_share['claim'])), 'paid_low': figure(low_share['paid'], C.usd(low_share['paid']))},
                figure='low', kind='measured', bearing='sizes',
                detail='In FY%d the claim was %s and the payment %s. The shortfall in a pro-rated year lands on the town’s budget with no warning the district can act on, '
                       'because the rate is not known until the state’s books close. That is the sense in which this line is unforecastable from Lunenburg.'
                       % (low_share['fy'], C.usd(low_share['claim']), C.usd(low_share['paid'])),
                basis='`dese_circuit_breaker`, total_quarterly_payment divided by total_net_claim, Lunenburg rows, every year.',
                not_shown='The appropriation itself, or why any year was short. The state file gives the result, not the vote.',
                allow=('75%', '70%'),
                see=[('/state-aid', 'The rest of what the state sends')],
            ),
            conclusion(
                id='the-threshold-is-a-deduction-not-a-rate',
                claim='In FY%d the state deducted %s per child before reimbursing anything — %s in all.'
                      % (last['fy'], C.usd(last['threshold_per_child']), C.usd(last['threshold'])),
                so_what='The district pays the first %s of every claimed child, then gets about three-quarters of the rest.'
                        % C.usd(last['threshold_per_child']),
                figures={'per_child': figure(last['threshold_per_child'], C.usd(last['threshold_per_child']), 'deducted per child, FY%d' % last['fy']),
                         'total': figure(last['threshold'], C.usd(last['threshold'])),
                         'elig': figure(last['eligible'], C.usd(last['eligible'])), 'paid': figure(last['paid'], C.usd(last['paid'])),
                         'share_elig': figure(last['paid_share_of_eligible'], C.pct(100 * last['paid_share_of_eligible'])),
                         'fy': figure(last['fy'], 'FY%d' % last['fy'])},
                figure='per_child', kind='measured', bearing='sizes',
                detail='Of %s in eligible expenses the state paid %s — %s of the total, because the threshold comes off first and the share applies to what is left. '
                       'The threshold is four times the state’s average foundation budget per pupil and rises with it, so the district’s own share rises even when nothing about a placement changes.'
                       % (C.usd(last['eligible']), C.usd(last['paid']), C.pct(100 * last['paid_share_of_eligible'])),
                basis='`dese_circuit_breaker` threshold_amount divided by eligible_students_claimed; total_quarterly_payment over total_eligible_expenses.',
                not_shown='The foundation figure the threshold is four times of; DESE publishes the resulting threshold, not its derivation, in this file.',
            ),
            conclusion(
                id='transport-joined-the-reimbursement',
                claim='Since FY%d the state has also reimbursed special education transport: %s in FY%d.'
                      % (transport_first['fy'], C.usd(last['transport']), last['fy']),
                so_what='New money: from %s in its first year to a peak of %s in FY%d.'
                        % (C.usd(transport_first['transport']), C.usd(transport_peak['transport']), transport_peak['fy']),
                figures={'now': figure(last['transport'], C.usd(last['transport']), 'transport reimbursed, FY%d' % last['fy']),
                         'first': figure(transport_first['transport'], C.usd(transport_first['transport'])),
                         'fy_first': figure(transport_first['fy'], 'FY%d' % transport_first['fy']), 'fy': figure(last['fy'], 'FY%d' % last['fy']),
                         'peak': figure(transport_peak['transport'], C.usd(transport_peak['transport'])), 'fy_peak': figure(transport_peak['fy'], 'FY%d' % transport_peak['fy'])},
                figure='now', kind='measured', bearing='sizes',
                detail='Before FY%d the transport column is empty for every district; the reimbursement did not exist. It is a separate line from tuition and is included in the payment totals above.'
                       % transport_first['fy'],
                basis='`dese_circuit_breaker` reimb_transport, Lunenburg rows.',
                not_shown='What the district spends on special education transport in total; this is the reimbursed part only.',
            ),
            conclusion(
                id='lunenburgs-placements-cost-more-per-child-than-most-neighbours',
                claim='Lunenburg’s cost per claimed child, %s, is %s of %s districts in FY%d.'
                      % (C.usd(last['per_child']), ['highest', 'second highest', 'third highest'][lun_rank - 1] if lun_rank <= 3 else '%dth highest' % lun_rank,
                         C.num(len(pr)), last['fy']),
                so_what='The neighbours range from %s to %s per child; each is paid about the same share.'
                        % (C.usd(min(r['per_child'] for r in pr)), C.usd(max(r['per_child'] for r in pr))),
                figures={'lun': figure(last['per_child'], C.usd(last['per_child']), 'per claimed child, FY%d' % last['fy']),
                         'lo': figure(min(r['per_child'] for r in pr), C.usd(min(r['per_child'] for r in pr))),
                         'hi': figure(max(r['per_child'] for r in pr), C.usd(max(r['per_child'] for r in pr))),
                         'n': figure(len(pr), C.num(len(pr))), 'fy': figure(last['fy'], 'FY%d' % last['fy'])},
                figure='lun', kind='measured', bearing='sizes',
                detail='The table below gives each district’s children claimed, cost per child and share paid. Statewide, the same file counts %s children and %s in eligible expenses.'
                       % (C.num(st['k']), C.usd(st['e'])),
                basis='`dese_circuit_breaker`, FY%d district rows for Lunenburg and its neighbours; state row for the totals.' % last['fy'],
                not_shown='Whether a higher cost per child reflects the children’s needs, the placements chosen, or the prices charged. All three move it.',
                see=[('/what-other-districts-spend', 'The same districts, on spending')],
            ),
        ]
        # statewide figures registered in the last conclusion
        rows[-1]['figures']['state_kids'] = figure(st['k'], C.num(st['k']))
        rows[-1]['figures']['state_elig'] = figure(st['e'], C.usd(st['e']))
        return dict(
            generated_by='scripts/build_circuit_breaker.py',
            about='What the state reimbursed Lunenburg for its costliest special education placements, FY%d to FY%d, and how the mechanism decides it.' % (first['fy'], last['fy']),
            grain='DOLLARS PAID by fiscal year of payment, and a COUNT of children claimed, from DESE’s reimbursement file. A payment reimburses the previous year’s '
                  'spending. A child is claimed only if their cost exceeded the threshold; the many in placements below it are not here.',
            first_fy=first['fy'], last_fy=last['fy'],
            series=s, peers=pr, state=dict(fy=last['fy'], children=int(st['k']), eligible=st['e'], paid=st['p']),
            mechanism='For each child whose special education costs exceed four times the state average foundation budget per pupil, the state reimburses '
                      'up to 75% of the cost above that threshold, pro-rated to the year’s appropriation. Paid the following year.',
            sources=document(),
            not_established=[
                'Which placements or which children are behind any row; the file counts and sums.',
                'Why the count of claimed children fell from the high twenties to single digits after FY2016.',
                'What Lunenburg spends on special education transport in total; only the reimbursed part is here.',
            ],
            conclusions=emit('circuit-breaker', rows),
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
            print('STALE %s — run build_circuit_breaker.py' % os.path.relpath(OUT, ROOT))
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
