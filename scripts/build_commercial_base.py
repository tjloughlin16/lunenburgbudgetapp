#!/usr/bin/env python3
"""The commercial base, as the state certifies it: how big it is, year by year, and how
much of it was BUILT rather than revalued.

    python3 scripts/build_commercial_base.py           # write fy28/public/data/commercial-base.json
    python3 scripts/build_commercial_base.py --check   # fail if it no longer reproduces

TJ, 16 September 2026: "do we have data on the commercial development growth over the
LAST 5 years?" -- and, the same hour, the file he first exported started at FY2023 and
made a 41% boom out of four years. The full series changes the reading and this is the
full series: assessed value by class FY2002 onward and certified new growth FY2003
onward, both from the Division of Local Services (sources/state-dls/, by script).

TWO SERIES, BECAUSE THEY ANSWER TWO QUESTIONS.
  value by class   how big the commercial base IS. A revaluation moves it as much as a
                   building does: Lunenburg's homes were revalued up 23% in FY2023 with
                   nothing built, and the business SHARE of the base fell to its low that
                   year for no reason that had anything to do with business.
  new growth       what the assessors certified was ADDED -- new construction and new
                   personal property, valued and put on the levy limit -- split residential
                   against everything else. Total minus residential is building that is
                   not housing. This is the series that says what got built.

RULE 7. Every conclusion here is a measurement on those two files. Why non-residential
new growth stepped up in FY2024 -- which projects, which corridor, whose permit -- is not
in either file and is not stated. The town's own building permits would say, and they
are named in `not_established`.

RULE 8. The three years after the model's old anchor year were the three best on record
for non-residential building. That is credit the record gives the town, and it is stated
as plainly as the size of the plan it is set against.
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C                                           # noqa: E402
from conclusions import conclusion, emit, figure                  # noqa: E402

AV = os.path.join(ROOT, 'sources', 'data', 'dls-assessed-values.csv')
NG = os.path.join(ROOT, 'sources', 'data', 'dls-new-growth.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'commercial-base.json')
AV_KEY = 'state-dls/assessedvalues.xlsx'
NG_KEY = 'state-dls/new_growth.xlsx'
TOWN = 'Lunenburg'


def fail(msg):
    raise SystemExit('build_commercial_base: ' + msg)


def rows(path, total_col):
    out = [r for r in csv.DictReader(open(path, encoding='utf-8')) if r[total_col] not in ('', None)]
    if not out:
        fail('no certified rows in %s' % os.path.relpath(path, ROOT))
    return out


def values():
    out = []
    for r in rows(AV, 'total'):
        if r['municipality'] != TOWN:
            continue
        ci = round(float(r['commercial']) + float(r['industrial']))
        out.append(dict(fy=int(r['fy']), residential=round(float(r['residential'])),
                        commercial=round(float(r['commercial'])), industrial=round(float(r['industrial'])),
                        personal=round(float(r['personal_property'])), total=round(float(r['total'])),
                        commercial_industrial=ci, cip_share=round(float(r['cip_pct']), 2)))
    out.sort(key=lambda r: r['fy'])
    return out


def growth():
    out = []
    for r in rows(NG, 'total_value'):
        if r['municipality'] != TOWN:
            continue
        tv, rv = round(float(r['total_value'])), round(float(r['res_value']))
        out.append(dict(fy=int(r['fy']), total_value=tv, residential_value=rv, non_residential_value=tv - rv,
                        total_levy=round(float(r['total_levy'])), residential_levy=round(float(r['res_levy']))))
    out.sort(key=lambda r: r['fy'])
    return out


def peers():
    """Business's share of the base in the latest year, the eleven towns, so Lunenburg's
    share has something beside it. A share, so it compares across towns of different size."""
    by = {}
    for r in rows(AV, 'total'):
        by.setdefault(r['municipality'], []).append((int(r['fy']), float(r['cip_pct'])))
    latest = min(max(v)[0] for v in by.values())
    out = [dict(town=t, fy=latest, cip_share=round(dict(v)[latest], 2)) for t, v in by.items() if latest in dict(v)]
    out.sort(key=lambda r: -r['cip_share'])
    return out


def sources():
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = []
    for key, table, note in (
        (AV_KEY, 'Assessed Values by Class, FY2002–FY2026', 'Every class of property, every year, as certified. How big the base is.'),
        (NG_KEY, 'New Growth, residential and total, FY2003–FY2026', 'What the assessors certified was added each year, residential and all classes. What got built.'),
    ):
        r = man.get(key) or fail('%s is not in the manifest (rule 12)' % key)
        if not r['upstream']:
            fail('%s carries no upstream address (rule 12)' % key)
        out.append(dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']), url=r['upstream'],
                        docs_url='/docs/' + key, table=table, publisher='Massachusetts DOR, Division of Local Services', note=note))
    return out


def build():
    v, g = values(), growth()
    if len(v) < 20 or len(g) < 20:
        fail('only %d value years and %d new-growth years' % (len(v), len(g)))
    first, last = v[0], v[-1]
    # The most recent three certified years against the eleven before them, for
    # non-residential new growth. Three because the step is three years old; eleven
    # because FY2013 is where the post-recession series settles, and both spans are
    # stated on the card. A three-year window is a trend HERE (CLAUDE.md 7b).
    recent = g[-3:]
    before = [r for r in g if recent[0]['fy'] - 11 <= r['fy'] < recent[0]['fy']]
    avg_recent = sum(r['non_residential_value'] for r in recent) / len(recent)
    avg_before = sum(r['non_residential_value'] for r in before) / len(before)
    ranked = sorted(g, key=lambda r: -r['non_residential_value'])
    top3 = sorted(r['fy'] for r in ranked[:3])
    best = ranked[0]
    # Business's share: the peak, the low, and now.
    peak = max(v, key=lambda r: r['cip_share'])
    low = min(v, key=lambda r: r['cip_share'])
    # The two spans of commercial+industrial value: the long run to FY2022, and the step since.
    step_from = next(r for r in v if r['fy'] == recent[0]['fy'] - 2)   # the last year before the step in new growth showed in value
    long_pct = 100 * (step_from['commercial_industrial'] / first['commercial_industrial'] - 1)
    step_pct = 100 * (last['commercial_industrial'] / step_from['commercial_industrial'] - 1)
    step_add = last['commercial_industrial'] - step_from['commercial_industrial']
    long_add = step_from['commercial_industrial'] - first['commercial_industrial']
    res_step = next(r for r in v if r['fy'] == low['fy'])
    res_prev = next(r for r in v if r['fy'] == low['fy'] - 1)
    res_reval = 100 * (res_step['residential'] / res_prev['residential'] - 1)

    conclusions = [
        conclusion(
            id='non-residential-building-stepped-up',
            claim='Non-residential new growth ran %s times its prior eleven-year pace in FY%d–FY%d.'
                  % ('%.1f' % (avg_recent / avg_before), recent[0]['fy'], recent[-1]['fy']),
            so_what='%s a year against %s: the three best years for building that is not housing on record.'
                    % (C.usd(avg_recent), C.usd(avg_before)),
            figures={'avg_recent': figure(round(avg_recent), C.usd(avg_recent), 'of new non-residential value a year, FY%d–FY%d' % (recent[0]['fy'], recent[-1]['fy'])),
                     'avg_before': figure(round(avg_before), C.usd(avg_before)),
                     'fy_r0': figure(recent[0]['fy'], 'FY%d' % recent[0]['fy']), 'fy_r1': figure(recent[-1]['fy'], 'FY%d' % recent[-1]['fy']),
                     'years': figure(len(g), C.num(len(g))),
                     'best_fy': figure(best['fy'], 'FY%d' % best['fy']), 'best': figure(best['non_residential_value'], C.usd(best['non_residential_value'])),
                     'multiple': figure(avg_recent / avg_before, '%.1f' % (avg_recent / avg_before), 'times the FY%d–FY%d pace of non-residential new growth' % (before[0]['fy'], before[-1]['fy'])),
                     'top3': figure(top3, ', '.join('FY%d' % y for y in top3))},
            figure='multiple', kind='measured', bearing='sizes',
            detail='New growth is what the assessors certify was added to the tax rolls, valued, and the state publishes it split residential against all classes. '
                   'Total minus residential is building that is not housing. The three largest years in the record are %s; FY%d alone added %s. '
                   'The recent three-year average is %.1f times the eleven-year average before it.'
                   % (', '.join('FY%d' % y for y in top3), best['fy'], C.usd(best['non_residential_value']), avg_recent / avg_before),
            basis='DLS new growth file, Lunenburg rows: total new growth value minus residential new growth value, by fiscal year. '
                  'Averages over FY%d–FY%d and the eleven years before them.' % (recent[0]['fy'], recent[-1]['fy']),
            not_shown='WHAT was built, or where. The file carries a dollar of certified value and no parcel, permit or project. '
                      'Nor whether the pace holds: three years is the whole of the step. And personal property (equipment, utility plant) is inside the non-residential figure with the buildings.',
            see=[('/growth', 'What commercial growth would have to look like'), ('/try-growth', 'Try it: the growth dials')],
        ),
        conclusion(
            id='business-share-of-the-base',
            claim='Business is %s of the tax base in FY%d; %s at the FY%d peak, %s at the FY%d low.'
                  % (C.pct(last['cip_share']), last['fy'], C.pct(peak['cip_share']), peak['fy'], C.pct(low['cip_share']), low['fy']),
            so_what='The share moves with home prices more than with building: the FY%d low was a %s home revaluation.' % (low['fy'], C.pct(res_reval, 0)),
            figures={'share_now': figure(last['cip_share'], C.pct(last['cip_share']), 'of assessed value that is commercial, industrial or personal property, FY%d' % last['fy']),
                     'share_peak': figure(peak['cip_share'], C.pct(peak['cip_share'])), 'share_low': figure(low['cip_share'], C.pct(low['cip_share'])),
                     'fy_now': figure(last['fy'], 'FY%d' % last['fy']), 'fy_peak': figure(peak['fy'], 'FY%d' % peak['fy']), 'fy_low': figure(low['fy'], 'FY%d' % low['fy']),
                     'res_reval': figure(res_reval, C.pct(res_reval, 0)),
                     'cip_now': figure(last['commercial'] + last['industrial'] + last['personal'], C.usd(last['commercial'] + last['industrial'] + last['personal'])),
                     'total_now': figure(last['total'], C.usd(last['total']))},
            figure='share_now', kind='measured', bearing='sizes',
            detail='One tax rate, so a class’s share of assessed value is its share of the bill. Commercial, industrial and personal property are %s of %s in FY%d. '
                   'In FY%d residential value was revalued up %s in a single year and business’s share fell to %s with no business lost; the share is a ratio and the denominator is mostly homes.'
                   % (C.usd(last['commercial'] + last['industrial'] + last['personal']), C.usd(last['total']), last['fy'], low['fy'], C.pct(res_reval, 0), C.pct(low['cip_share'])),
            basis='DLS assessed values by class, Lunenburg rows, the CIP share as printed; the FY%d residential step is FY%d over FY%d residential value.' % (low['fy'], low['fy'], low['fy'] - 1),
            not_shown='Whether a larger business share would lower anybody’s bill. Proposition 2½ sets what the town collects; a share moves who owes what part of it. The crisis page prices that separately.',
            see=[('/try-growth', 'Try it: the growth dials')],
        ),
        conclusion(
            id='commercial-value-long-run',
            claim='Business property value: +%s in four years to FY%d, +%s in the %d before.'
                  % (C.usd(step_add), last['fy'], C.usd(long_add), step_from['fy'] - first['fy']),
            so_what='Up %s in four years after %s over %d. Part built, part revalued; this series cannot split them.'
                    % (C.pct(step_pct, 0), C.pct(long_pct, 0), step_from['fy'] - first['fy']),
            figures={'long_pct': figure(long_pct, C.pct(long_pct, 0)),
                     'step_pct': figure(step_pct, C.pct(step_pct, 0)),
                     'step_add': figure(step_add, C.usd(step_add), 'of commercial and industrial value added, FY%d to FY%d' % (step_from['fy'], last['fy'])),
                     'long_add': figure(long_add, C.usd(long_add)),
                     'fy_first': figure(first['fy'], 'FY%d' % first['fy']), 'fy_step': figure(step_from['fy'], 'FY%d' % step_from['fy']), 'fy_last': figure(last['fy'], 'FY%d' % last['fy']),
                     'span': figure(step_from['fy'] - first['fy'], C.num(step_from['fy'] - first['fy'])),
                     'ci_first': figure(first['commercial_industrial'], C.usd(first['commercial_industrial'])),
                     'ci_step': figure(step_from['commercial_industrial'], C.usd(step_from['commercial_industrial'])),
                     'ci_last': figure(last['commercial_industrial'], C.usd(last['commercial_industrial']))},
            figure='step_add', kind='measured', bearing='sizes',
            detail='Commercial plus industrial assessed value: %s in FY%d, %s in FY%d, %s in FY%d. Personal property is left out here because it is equipment and utility plant, not buildings.'
                   % (C.usd(first['commercial_industrial']), first['fy'], C.usd(step_from['commercial_industrial']), step_from['fy'], C.usd(last['commercial_industrial']), last['fy']),
            basis='DLS assessed values by class, Lunenburg rows, commercial plus industrial, as printed.',
            not_shown='How much of the step is construction and how much is the assessors revaluing what stood. The new-growth series above is the part that was built; the rest of the step is revaluation, and the two are not reconciled here.',
            see=[('/growth', 'The report this feeds')],
        ),
    ]
    return dict(
        generated_by='scripts/build_commercial_base.py',
        about='The commercial base as the state certifies it, FY%d to FY%d: how big it is, what share of the town it is, and how much of it was built rather than revalued.' % (first['fy'], last['fy']),
        grain='Dollars of ASSESSED VALUE, as the Division of Local Services publishes them for every town: the base by class each fiscal year, and the new growth the assessors certified was added. Not buildings, permits or businesses.',
        first_fy=first['fy'], last_fy=last['fy'],
        values=v, new_growth=g, peers=peers(),
        step=dict(from_fy=recent[0]['fy'], to_fy=recent[-1]['fy'], avg_non_residential=round(avg_recent),
                  before_from_fy=before[0]['fy'], before_to_fy=before[-1]['fy'], avg_non_residential_before=round(avg_before)),
        sources=sources(),
        not_established=[
            'What was built. The state certifies a dollar of new value per class and year; the town’s building permits and the assessors’ new-growth worksheets name the parcels, and neither is in the archive.',
            'How much of the rise in commercial value since FY%d is construction and how much revaluation; new growth is the built part and the remainder is not reconciled to it here.' % step_from['fy'],
            'Whether the FY%d–FY%d pace continues. Three years is the whole of the step.' % (recent[0]['fy'], recent[-1]['fy']),
        ],
        conclusions=emit('growth', conclusions),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_commercial_base.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the two DLS extracts' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: FY%d–FY%d, %d conclusions; non-residential new growth %s a year FY%d–FY%d vs %s before'
          % (os.path.relpath(OUT, ROOT), data['first_fy'], data['last_fy'], len(data['conclusions']),
             C.usd(data['step']['avg_non_residential']), data['step']['from_fy'], data['step']['to_fy'], C.usd(data['step']['avg_non_residential_before'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
