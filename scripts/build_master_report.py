#!/usr/bin/env python3
"""One report over all of them: every conclusion this project has reached, in one place.

    python3 scripts/build_master_report.py
    python3 scripts/build_master_report.py --check

WHAT THIS IS FOR

TJ: *"across all the drill-ins, I want to put together a sort of ONE REPORT TO RULE THEM
ALL that captures the most important conclusions... The data is not to call out the school
committee's faults. The point is to find insights in the data that we as a community might
want to understand, and especially anything that gives the story behind the financial
data."*

Sixteen reports is sixteen visits, and nobody makes sixteen visits. A resident who has
heard that special education is expensive, that the schools handed money back, and that
the state does not pay its share should be able to read what the data says about all three
in one sitting.

THE ONE ARCHITECTURAL RULE, AND EVERYTHING ELSE FOLLOWS FROM IT

**This file writes no claims. It reads them.** Every conclusion here is computed by the
generator that computed its figures and published in that report's own payload -- see
`scripts/conclusions.py`. A synthesis that restated its sources would be the same defect
this project has hit a dozen times: something derived written down, the thing it derived
from moving, and nothing connecting the two. So the master report cannot say anything a
report does not, because it has nothing of its own to say it with.

AND IT FAILS CLOSED. A routed report with no conclusions is NAMED on the page, in its own
section, rather than quietly left out. A synthesis that silently drops a report is worse
than one that admits a hole: the hole is visible and can be filled, and the silent drop
reads, to every reader, as coverage.

WHAT IS DERIVED RATHER THAN LISTED, and why each one

  * WHICH REPORTS EXIST -- read off `AREA_TABS.analyses` in routes.ts, through
    `build_reports_index.routed_reports()`, which is the same table the app itself routes
    on. A hand-kept list of one's own pages is the artefact that goes stale first. That
    generator already refuses to write if a routed report has no page component, so this
    one inherits the check.

  * WHICH CONCLUSION IS A REPORT'S HEADLINE -- the FIRST one in its array. That is a
    contract stated in `conclusions.py` and kept by the generators, so the ordering
    decision lives where the knowledge is rather than in a table here.

  * THE MEASURED / HYPOTHESIS SPLIT -- rule 7, read off each conclusion's own `kind`. A
    figure is a fact and an explanation for it is not, and the two are never set in one
    voice. Counted here so the page can say how much of it is which.

  * THE WRITTEN ANALYSES -- the Markdown documents in `sources/analyses/`, which carry no
    machine-readable conclusions at all. They are listed as exactly that, so nobody reads
    this page as the whole of what this project has concluded.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from build_reports_index import routed_reports          # noqa: E402
import conclusions as C                                 # noqa: E402

DATA = os.path.join(ROOT, 'fy28', 'public', 'data')
ANALYSES = os.path.join(ROOT, 'sources', 'analyses')
OUT = os.path.join(DATA, 'what-it-all-adds-up-to.json')

# The report that IS this page. It has no conclusions of its own by construction -- it
# holds everybody else's -- so it is not a hole in its own coverage.
SELF = 'addsup'

# `analysis` is not a report. It is the ONE tab that renders all seventeen Markdown
# documents, `/analysis/<id>`, so it has no payload, no conclusions and no single subject.
# The documents themselves are listed in their own section further down.
#
# `sped` is the four-report CHOOSER at /special-education. It is not a report either: its
# job is to say, before a reader opens any of them, that the four do not combine. It reads
# one of their payloads to put counts on its cards, which is why it has to be named here
# rather than detected -- without this it resolves to sped-students.json and this page
# prints that report's conclusions twice under two different titles. The four are each
# covered on their own below.
NOT_A_REPORT = ('analysis', 'sped')


def payload_of(rep):
    """A routed report's published payload, or None where it has one and it is missing."""
    if not rep.get('data'):
        return None
    p = os.path.join(ROOT, 'fy28', 'public', rep['data']['url'].lstrip('/'))
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def written_analyses():
    """The Markdown analyses, which state their conclusions in prose and not in a payload.

    Listed rather than parsed. A regex that lifted sentences out of a document and
    presented them as conclusions would be exactly the derived-quoted-as-observed error
    rule 13 is about -- the document says what it says, and the honest thing is to name it
    and link to it.
    """
    out = []
    for f in sorted(os.listdir(ANALYSES)):
        if not f.endswith('.md'):
            continue
        text = open(os.path.join(ANALYSES, f), encoding='utf-8').read()
        title = text.split('\n', 1)[0].lstrip('# ').strip()
        out.append({'id': f[:-3], 'title': title,
                    'url': '/analysis/' + f[:-3],
                    'doc_url': '/docs/analyses/' + f,
                    'words': len(re.findall(r'\S+', text))})
    if not out:
        raise SystemExit('sources/analyses/ holds no documents -- the join matched '
                         'nothing, which reads exactly like an archive with no analyses '
                         'in it. Refusing to write.')
    return out


def build():
    reports, _undescribed = routed_reports(all_of_area=True)

    rows, headlines, holes = [], [], []
    measured = hypothesis = 0
    # WHAT A READER CAN DO WITH EACH ONE, counted out loud.
    #
    # TJ's complaint about this page was that the conclusions "come off as 'interesting'
    # but not clear as to why they are 'important'". `bearing` is that distinction --
    # `sizes` establishes how big something is or how it got this way, `lever` points at
    # something a body in this town can actually decide.
    #
    # UNCLASSIFIED IS COUNTED AND NAMED rather than defaulted to either. A conclusion
    # nobody has judged is not the same as one judged to be context, and quietly filing it
    # as context would hide exactly the thing this field exists to surface.
    bearing_counts = {'sizes': 0, 'lever': 0, 'unclassified': 0}
    for rep in reports:
        if rep['id'] == SELF or rep['id'] in NOT_A_REPORT:
            continue
        d = payload_of(rep) or {}
        cs = d.get('conclusions') or []
        for c in cs:
            if c['kind'] == 'hypothesis':
                hypothesis += 1
            else:
                measured += 1
            bearing_counts[c.get('bearing') or 'unclassified'] += 1
        row = {
            'id': rep['id'], 'title': rep['title'], 'url': rep['url'],
            'about': rep['about'], 'generator': rep['generator'],
            'data': (rep['data'] or {}).get('url'),
            'conclusions': cs, 'count': len(cs),
        }
        rows.append(row)
        if cs:
            headlines.append({'report': rep['id'], 'report_title': rep['title'],
                              'report_url': rep['url'], **cs[0]})
        else:
            # FAIL CLOSED. Named, with the reason, rather than dropped. `sped` is the
            # four-report chooser and has no payload of its own; anything else here is a
            # report whose generator has not been given conclusions yet, and saying so is
            # the point of this list.
            holes.append({
                'id': rep['id'], 'title': rep['title'], 'url': rep['url'],
                'why': ('This is a chooser rather than a report — its four reports each '
                        'carry their own conclusions.') if not rep.get('data') else
                       ('Its generator does not yet publish conclusions, so nothing on '
                        'this page speaks for it. Read the report itself.'),
            })

    # BY SUBJECT, from the single declaration in conclusions.py. TJ: "the one big report
    # needs to have categorical sections too... special education, finances, athletics,
    # etc." The order of reports inside a topic is the order they were placed above, which
    # is the bar's order with each hidden report behind its own door.
    by_id = {r['id']: r for r in rows}
    topics = []
    for key, title, blurb, tabs in C.TOPICS:
        got = [by_id[t] for t in tabs if t in by_id and by_id[t]['count']]
        if got:
            topics.append(dict(key=key, title=title, about=blurb,
                               reports=got,
                               conclusions=sum(r['count'] for r in got)))
    placed = {t for _k, _t, _b, tabs in C.TOPICS for t in tabs}
    stray = sorted(r['id'] for r in rows if r['id'] not in placed)
    if stray:
        raise SystemExit(
            'these reports are in no topic in conclusions.TOPICS, so this page would '
            'carry their headline and then never show them again: %s' % ', '.join(stray))

    docs = written_analyses()
    if not rows:
        raise SystemExit('no routed reports were found in AREA_TABS.analyses -- refusing '
                         'to write a synthesis of nothing.')
    if not headlines:
        raise SystemExit('not one routed report publishes conclusions. A master report '
                         'with no conclusions in it is a page that lies by existing.')

    return {
        'about': 'Every conclusion this project has reached, read out of the reports that '
                 'computed them rather than restated here.',
        'generated_by': 'scripts/build_master_report.py',
        'reports': rows,
        'topics': topics,
        'headlines': headlines,
        'not_covered': holes,
        'documents': docs,
        'totals': {
            'reports': len(rows),
            'with_conclusions': len([r for r in rows if r['count']]),
            'without_conclusions': len(holes),
            'conclusions': measured + hypothesis,
            'measured': measured,
            'bearing': bearing_counts,
            'hypothesis': hypothesis,
            'documents': len(docs),
            'document_words': sum(d['words'] for d in docs),
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()
    rel = os.path.relpath(OUT, ROOT)

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % rel)
            return 1
        with open(OUT, encoding='utf-8') as fh:
            if json.load(fh) != data:
                print('STALE %s — run: python3 scripts/build_master_report.py' % rel)
                return 1
        print('ok — %s reproduces from every report payload' % rel)
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    t = data['totals']
    print('%s' % rel)
    print('  %d conclusions from %d of %d routed reports — %d measured, %d hypothesis'
          % (t['conclusions'], t['with_conclusions'], t['reports'], t['measured'],
             t['hypothesis']))
    if data['not_covered']:
        print('  NOT COVERED, and named on the page: %s'
              % ', '.join(h['id'] for h in data['not_covered']))
    print('  plus %d written analyses, %s words, which carry no machine-readable '
          'conclusions' % (t['documents'], format(t['document_words'], ',d')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
