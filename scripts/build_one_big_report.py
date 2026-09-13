#!/usr/bin/env python3
"""THE ONE BIG REPORT, told as a story by category, from a spec TJ edits in a spreadsheet.

    python3 scripts/build_one_big_report.py          # write fy28/public/data/one-big-report.json
    python3 scripts/build_one_big_report.py --check  # fail if it no longer reproduces

THE SPEC IS A CSV, sources/data/one-big-report-story.csv, one row per thing on the page:

    story_order, category, role, kind, ref, label, note

  * `category` is a section heading, in the order the letters sort: the hole and what fixes
    it, who lives here, the students, special education, the people who work in the
    schools, where the money comes from, what it costs against others, what families pay,
    what is taught.
  * `role` is headline | supporting | context -- the most important metric first, then the
    conclusions that deepen it, then the rows of context (a year-by-year table, a ranked
    list) at the bottom of the section. TJ, 13 September 2026: "organize this data by
    category ... list the metrics out with almost a story, starting with the most important
    metrics and building with more and more deeper context."
  * `kind` is bigpicture (a figure from big-picture.json, addressed by `ref`) or conclusion
    (`report_id/conclusion_id`, read from that report's own published payload).

NOTHING HERE IS WRITTEN. A bigpicture ref is rendered from the figure the model computed;
a conclusion is the report's own row, verbatim, with the report's title and URL beside it.
The spec can only ARRANGE what the reports say, never restate it -- which is the same
architecture the digest had, with an editor's hand on the order.

It fails closed: a ref that resolves to nothing stops the build, because a row that silently
vanishes from a page a resident is reading is worse than a build that says so.
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_reports_index import routed_reports          # noqa: E402
from build_master_report import payload_of              # noqa: E402

SPEC = os.path.join(ROOT, 'sources', 'data', 'one-big-report-story.csv')
BIG = os.path.join(ROOT, 'fy28', 'public', 'data', 'big-picture.json')
DATA = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT = os.path.join(DATA, 'one-big-report.json')
ROLES = ('headline', 'supporting', 'context')


def fail(msg):
    print('FAIL: ' + msg)
    raise SystemExit(1)


usd = lambda n: '$' + format(round(n), ',')
pct = lambda x, d=0: ('%.' + str(d) + 'f%%') % (x * 100)
n1 = lambda x: '%.1f' % x
FY = lambda fy: 'FY%s' % str(fy)[2:]
LINE = dict(salaries='Salaries', health='Health insurance', transport='Transportation',
            sped='Special education, in district', sped_tuition='Out-of-district special education',
            utilities='Utilities', other='Everything else')


def bigpicture_item(b, ref):
    """One figure from big-picture.json: value, label and one line, all computed there."""
    h, o, dr, dev, f = b['hole'], b['overrides'], b['drivers'], b['development'], b['facts']
    y0, yN = h['years'][0], h['years'][-1]
    if ref == 'hole.short_next':
        return dict(value=usd(y0['short']), label='short next year', sub='%s, at level service' % FY(y0['fy']), grain='a projection: the model’s rates run forward', tone='critical')
    if ref == 'hole.total':
        return dict(value=usd(h['total']), label='short over five years', sub='%s–%s, after each year’s cuts stay cut' % (FY(y0['fy']), FY(yN['fy'])))
    if ref == 'hole.cum_fte':
        return dict(value=n1(yN['cum_fte']), label='positions gone by %s' % FY(yN['fy']), sub='if it is closed by cutting, in the order the School Committee has said')
    if ref.startswith('hole.year.'):
        y = next(x for x in h['years'] if x['fy'] == int(ref.split('.')[-1]))
        return dict(value=usd(y['short']), label='short in %s' % FY(y['fy']), sub='%s positions cut; %s' % (n1(y['fte']), ' · '.join(y['takes'])))
    if ref.startswith('override.'):
        r = next(x for x in o['rows'] if x['amount'] == int(ref.split('.')[-1]))
        return dict(value='%d years' % r['years'], label='a %s school override holds' % ('$%.0fM' % (r['amount'] / 1e6)), sub='reopens %s; about %s a year on the average bill, permanently' % (FY(r['reopens_fy']), usd(r['on_average_home'])))
    if ref == 'drivers.blended':
        return dict(value=pct(dr['blended'], 2), label='costs grow a year', sub='blended across every line, at the model’s rates')
    if ref == 'drivers.cap':
        return dict(value=pct(dr['cap'], 1), label='the levy grows a year', sub='Proposition 2½, before new growth')
    if ref == 'drivers.top3':
        pos = [r for r in dr['rows'] if r['pull'] > 0]
        top3 = sum(r['pull'] for r in dr['rows'][:3]) / sum(r['pull'] for r in pos)
        return dict(value=pct(top3), label='of the excess is three lines', sub='health insurance, in-district special education, salaries — none set by the School Committee')
    if ref.startswith('drivers.pull.'):
        r = next(x for x in dr['rows'] if x['key'] == ref.split('.')[-1])
        return dict(value='%.2f pts' % (r['pull'] * 100), label=r['label'], sub='%s of spending, growing %s a year — %s' % (pct(r['share']), pct(r['rate'], 1), r['who']))
    if ref == 'development.value':
        return dict(value='$%.1fM' % (dev['value'] / 1e6), label='of new taxable value for $1M a year', sub='%s typical developments at once; %s of the town’s value added' % (n1(dev['at_once']), pct(dev['share_of_town'], 1)))
    c = f['census']
    ch = lambda x, unit, d=0: '%s → %s, %s to %s (%s)' % (format(x['first'], ',.%df' % d), format(x['last'], ',.%df' % d), FY(x['first_fy']), FY(x['last_fy']), ('%+.0f%%' % (x['pct'] * 100)) if x.get('pct') is not None else '')
    if ref == 'facts.households_with_child':
        return dict(value=pct(c['households_with_child']['share'] / 100), label='of households have a child under 18', sub='%s of %s, ± %.1f points, ACS %s' % (format(round(c['households_with_child']['n']), ','), format(round(c['households_with_child']['of']), ','), c['households_with_child']['share_moe'], c['window']))
    if ref == 'facts.seniors':
        return dict(value=pct(c['seniors']['share'] / 100), label='of residents are 65 or over', sub='%s, ± %.1f points, ACS %s' % (format(round(c['seniors']['n']), ','), c['seniors']['share_moe'], c['window']))
    if ref == 'facts.children':
        return dict(value=pct(c['children']['share'] / 100), label='of residents are under 18', sub='%s, ± %.1f points' % (format(round(c['children']['n']), ','), c['children']['share_moe']))
    if ref == 'facts.students':
        return dict(value=format(round(f['students']['last']), ','), label='students', sub=ch(f['students'], 'students') + ' — flat for a decade', grain=f['students']['grain'])
    if ref == 'facts.low_income':
        x = f['low_income']
        return dict(value=pct(x['last']), label='of students are low-income', sub='from %s in %s, as DESE counts it' % (pct(x['first']), FY(x['first_fy'])))
    if ref == 'facts.disabilities':
        x = f['disabilities']
        return dict(value=pct(x['last']), label='of students have a disability', sub='from %s in %s, DESE' % (pct(x['first']), FY(x['first_fy'])))
    if ref == 'facts.state_aid':
        x = f['state_aid']
        return dict(value=pct(x['share']), label='of the school budget is state aid', sub='%s of %s, FY26 — set in the Governor’s budget, not in town' % (usd(x['aid']), usd(x['appropriation'])))
    if ref == 'facts.teachers':
        return dict(value=n1(f['teachers']['last']), label='teacher FTE', sub=ch(f['teachers'], 'FTE', 1), grain=f['teachers']['grain'])
    if ref == 'facts.paras':
        return dict(value=format(round(f['paras']['last']), ','), label='paraprofessional FTE', sub=ch(f['paras'], 'FTE') + ' — the line that grew', grain=f['paras']['grain'])
    if ref == 'facts.total_per_pupil':
        x = f['admin_per_pupil']['total_per_pupil']
        return dict(value=usd(x['last']), label='spent for each pupil, all funds', sub=ch(x, '$'), grain='DESE end-of-year report, every fund')
    if ref == 'facts.athletes':
        x = f['athletes']
        return dict(value=format(round(x['last']), ','), label='athletes, by season', sub='%s → %s, %s to %s — the %d years published' % (format(round(x['first']), ','), format(round(x['last']), ','), FY(x['first_fy']), FY(x['last_fy']), x['years']), grain=x['grain'])
    fail('big-picture ref %r is not one this generator knows how to render' % ref)


def load_conclusions():
    """Every routed report's conclusions, keyed report/id, with title and URL."""
    out = {}
    reports, _undescribed = routed_reports(all_of_area=True)
    for r in reports:
        d = payload_of(r) or {}
        for c in d.get('conclusions') or []:
            out['%s/%s' % (r['id'], c['id'])] = dict(c, report=r['id'], report_title=r['title'], report_url=r['url'])
    return out


def build():
    b = json.load(open(BIG, encoding='utf-8'))
    concl = load_conclusions()
    spec = list(csv.DictReader(open(SPEC, encoding='utf-8')))
    if not spec:
        fail('the story spec is empty')
    sections, order = {}, []
    for row in sorted(spec, key=lambda r: int(r['story_order'])):
        cat = row['category']
        if row['role'] not in ROLES:
            fail('row %s: role %r is not one of %s' % (row['story_order'], row['role'], ROLES))
        if cat not in sections:
            sections[cat] = dict(key=cat.split('.')[0].strip().lower(), title=cat.split('. ', 1)[1] if '. ' in cat else cat,
                                 headline=[], supporting=[], context=[])
            order.append(cat)
        if row['kind'] == 'bigpicture':
            item = dict(kind='bigpicture', ref=row['ref'], **bigpicture_item(b, row['ref']))
        elif row['kind'] == 'conclusion':
            c = concl.get(row['ref'])
            if not c:
                fail('row %s: conclusion %r is not in any routed report’s payload' % (row['story_order'], row['ref']))
            item = dict(kind='conclusion', ref=row['ref'], conclusion=c)
        else:
            fail('row %s: kind %r' % (row['story_order'], row['kind']))
        if row.get('note'):
            item['note'] = row['note']
        sections[cat][row['role']].append(item)
    secs = [sections[c] for c in order]
    n_big = sum(1 for s in secs for r in ROLES for i in s[r] if i['kind'] == 'bigpicture')
    n_con = sum(1 for s in secs for r in ROLES for i in s[r] if i['kind'] == 'conclusion')
    reports = sorted({i['conclusion']['report'] for s in secs for r in ROLES for i in s[r] if i['kind'] == 'conclusion'})
    return dict(
        about=('The numbers that frame Lunenburg’s school budget problem, by subject, each one starting with the figure '
               'that matters most and building down into the context — arranged by an editor, computed by the reports.'),
        sections=secs, spec=os.path.relpath(SPEC, ROOT),
        totals=dict(sections=len(secs), figures=n_big, conclusions=n_con, reports=len(reports)),
        reports=reports, generated_by='scripts/build_one_big_report.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_one_big_report.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the spec and the payloads' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    t = data['totals']
    print('%s: %d sections, %d figures, %d conclusions from %d reports'
          % (os.path.relpath(OUT, ROOT), t['sections'], t['figures'], t['conclusions'], t['reports']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
