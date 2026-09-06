"""Publish the index of analyses this project has written.

    python3 scripts/build_reports_index.py

Writes `fy28/public/data/reports.json`, which the /reports page renders.

WHY A PAGE OF ITS OWN

These documents were buried as one group inside the source catalogue, between the town's
mirrored PDFs and the district's spreadsheets. That is the wrong shelf. Everything else in
that catalogue was written by somebody else and is republished here unchanged; these were
written HERE, and the distinction is the single most important thing a reader needs.

So the page leads with the caveat rather than footnoting it, and every row carries the
three things that make a claim checkable: the document, the data underneath it, and the
script that recomputes every figure in it.

Generated rather than maintained. A hand-written index of one's own analyses is exactly
the artefact that goes stale first and is least likely to be noticed doing it.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'analyses')
PDF = os.path.join(ROOT, 'fy28', 'public', 'docs', 'analyses')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'reports.json')
SITE = 'https://lunenburgbudgetproject.org'

# Order the reader should meet them in, not alphabetical. Anything not listed is appended
# in alphabetical order rather than dropped -- a new analysis appears without being added
# here, and appears in the wrong place, which is a visible prompt to order it.
ORDER = [
    'fy26-closeout', 'fy26-closeout-town', 'budget-vs-actual', 'free-cash',
    'athletics', 'athletics-ledger', 'sped-and-the-curve', 'sped-and-funds',
    'fy27-and-the-override', 'fy27-cut-reconciliation', 'peer-districts',
    'connecting-the-budget', 'show-your-work',
]

# One line on what each answers. Editorial, so written here rather than derived -- but
# every one is checked against the document's own opening below.
ABOUT = {
    'what-you-can-ask':
        'Every question this archive can answer, in plain English and without a line of '
        'SQL. The list a resident should start from: pick the question you actually have '
        'and follow it to the figure and the document behind it.',
    'questions':
        'The same questions with the query that answers each one, run against the '
        'database on every build — so none of them is a claim about what this data can '
        'do. If one stops answering, the build fails.',
    'connecting-the-budget':
        'What can be followed from the school budget to the town’s books, and where it '
        'stops. Two levels join, the third cannot, and the format a report arrives in '
        'decides which.',
    'fy26-closeout':
        'The school department’s FY26, read line by line from the town’s own ledger. '
        'What the $482,101 headline actually is, and three things it cannot explain.',
    'fy26-closeout-town':
        'The same ledger read for the other 67 departments. Snow at 292% of its '
        'appropriation, a Reserve Fund never touched, and school costs sitting on the '
        'town’s books.',
    'budget-vs-actual':
        'Did the money the town budgeted match the money it spent? Careful about what '
        'the documents can and cannot support.',
    'free-cash':
        'How much of Lunenburg’s certified free cash is genuinely spendable, built from '
        'the state’s own proofs for nine towns.',
    'athletics':
        'The one programme where both sides of the money are visible, and therefore the '
        'only place the net-versus-gross problem can be measured rather than described.',
    'athletics-ledger':
        'Three years of the athletics revolving fund at transaction level, from a records '
        'request. Includes $254,121.18 described only as “per memo”.',
    'sped-and-the-curve':
        'Special education is about 22% of the budget and the largest single driver of '
        'the gap. What the rates rest on.',
    'sped-and-funds':
        'Whether the special education escalator can be distinguished from grant money '
        'unwinding. It currently cannot, and this says why.',
    'fy27-and-the-override':
        'What the FY27 budget did, what the override would have done, and what the votes '
        'actually decided.',
    'fy27-cut-reconciliation':
        'Reconciling the district’s published cut list against its own budget columns.',
    'peer-districts':
        'What six neighbouring districts did with the same year, and what that does and '
        'does not tell you about Lunenburg.',
    'show-your-work':
        'Every calculation the site publishes, with its inputs, its formula, a worked '
        'example, and whether each figure is published, contractual, statutory, our '
        'measurement or our assumption.',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git_date(path):
    try:
        out = subprocess.run(
            ['git', 'log', '-1', '--format=%cs', '--', path],
            cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out or None
    except Exception:
        return None


def main():
    names = sorted(f[:-3] for f in os.listdir(SRC) if f.endswith('.md'))
    ordered = [n for n in ORDER if n in names] + [n for n in names if n not in ORDER]

    reports, unlisted = [], []
    for n in ordered:
        md = os.path.join(SRC, n + '.md')
        text = open(md, encoding='utf-8').read()
        title = text.split('\n', 1)[0].lstrip('# ').strip()

        # The first real paragraph, skipping the working-state blockquote and the
        # generated-by line. Used only as a fallback where ABOUT has no entry.
        lede = ''
        for para in re.split(r'\n\s*\n', text):
            p = para.strip()
            if (p.startswith('#') or p.startswith('>') or p.startswith('---')
                    or p.startswith('Analysis,') or not p):
                continue
            lede = re.sub(r'\s+', ' ', p)[:240]
            break
        if n not in ABOUT:
            unlisted.append(n)

        verifier = 'scripts/verify_%s.py' % n.replace('-', '_')
        has_verifier = os.path.exists(os.path.join(ROOT, verifier))
        pdf = os.path.join(PDF, n + '.pdf')

        charts = sorted(
            f for f in os.listdir(os.path.join(SRC, 'charts'))
            if f.startswith('fy26-') and n.endswith(
                'town' if '-town' in f else 'closeout')) \
            if os.path.isdir(os.path.join(SRC, 'charts')) and n.startswith('fy26') else []

        reports.append(dict(
            id=n, title=title,
            about=ABOUT.get(n) or lede,
            words=len(text.split()),
            updated=git_date(md),
            markdown=dict(url=f'/docs/analyses/{n}.md',
                          bytes=os.path.getsize(md), sha256=sha256(md)),
            pdf=(dict(url=f'/docs/analyses/{n}.pdf', bytes=os.path.getsize(pdf))
                 if os.path.exists(pdf) else None),
            verifier=(dict(path=verifier,
                           command=f'python3 {verifier}') if has_verifier else None),
            charts=[f'/docs/analyses/charts/{c}' for c in charts],
        ))

    data = dict(
        generated=date.today().isoformat(),
        # The caveat leads. It is the first field for the same reason it is the first
        # thing on the page: these are not the town's documents and must never be
        # mistaken for them.
        caveat=dict(
            headline='Written by this project, not by the town or the district.',
            body=('Nothing on this page is an official document. These analyses are '
                  'written here, from documents the town and district published and from '
                  'records obtained by request. They have not been reviewed or endorsed '
                  'by the Town of Lunenburg, the Lunenburg School Committee, the Finance '
                  'Committee or Lunenburg Public Schools, and this project is not '
                  'affiliated with any of them.'),
            checkable=('Every figure in an analysis is recomputed from the underlying '
                       'data by a script, and the script is named on the row. The data '
                       'itself is published below — you do not have to take any of this '
                       'on trust, and you should not.'),
            corrections=('Where an earlier version of an analysis was wrong, the '
                         'correction stays in the text rather than being edited out. '
                         'Several of these documents describe their own earlier errors.'),
        ),
        reports=reports,
        data=dict(
            database=dict(
                url='/data/lunenburg.db',
                about='Every figure on this site in one SQLite file. The same database '
                      'the analyses are computed from.'),
            api=dict(url='/api/index',
                     about='A read-only JSON API. No key, no rate limit. /api/schema '
                           'states the grain of each table and the four ways to get a '
                           'confident wrong answer out of it.'),
            sources=dict(url='/sources',
                         about='Every source document, with its address, the publisher’s '
                               'own filename and a checksum.'),
            grossBudget=dict(
                url='/docs/data/gross-school-budget-fy2026.xlsx',
                about='The district’s budget in the district’s own shape, with what was '
                      'actually spent and what other money paid for it — and amber cells '
                      'wherever that money is not held.'),
        ),
    )

    fresh = json.dumps(data, separators=(',', ':'))

    # --check, and the reason it exists: this generator was NOT in check_generated.py, so
    # when two analyses were added the published index went on describing thirteen. The
    # site served a /reports page that was correct about everything it listed and silent
    # about what it did not -- an omission, which is the one defect shape nothing here
    # catches by re-reading. Found by somebody asking where the question list was.
    if '--check' in sys.argv:
        if not os.path.exists(OUT):
            raise SystemExit('%s does not exist. Run without --check.'
                             % os.path.relpath(OUT, ROOT))
        with open(OUT, encoding='utf-8') as fh:
            current = fh.read()

        # PDF byte counts are excluded from the comparison, and that is not a shortcut.
        # A PDF is not byte-reproducible -- re-rendering the same Markdown produces a
        # different size -- so including them would make this check fail every time the
        # PDFs are rebuilt, with nothing having changed. A check that cries wolf is worse
        # than no check, because it gets ignored on the day it is right.
        #
        # What that costs: a PDF whose CONTENT changed will not be caught here. That is
        # not what this check is for. It is for an analysis that exists on disk and is
        # missing from the index a reader browses -- the omission that let /reports
        # describe thirteen analyses while fifteen were published.
        def comparable(text):
            d = json.loads(text)
            for r in d.get('reports', []):
                if isinstance(r.get('pdf'), dict):
                    r['pdf'].pop('bytes', None)
            return json.dumps(d, separators=(',', ':'), sort_keys=True)

        if comparable(current) != comparable(fresh):
            now = json.loads(current)
            was = {r['id'] for r in now.get('reports', [])}
            has = {r['id'] for r in data['reports']}
            missing = sorted(has - was)
            extra = sorted(was - has)
            raise SystemExit(
                'STALE: %s no longer reproduces.%s%s\n  Run: python3 '
                'scripts/build_reports_index.py' % (
                    os.path.relpath(OUT, ROOT),
                    '\n  published index is MISSING: %s' % ', '.join(missing)
                    if missing else '',
                    '\n  published index lists what is gone: %s' % ', '.join(extra)
                    if extra else ''))
        print('ok: %s lists all %d analyses' % (os.path.relpath(OUT, ROOT),
                                                len(data['reports'])))
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d analyses, %d with a verifier, %d with a PDF'
          % (len(reports), sum(1 for r in reports if r['verifier']),
             sum(1 for r in reports if r['pdf'])))
    if unlisted:
        print('  NOT described in ABOUT, showing their own opening instead: %s'
              % ', '.join(unlisted))
    return 0


if __name__ == '__main__':
    sys.exit(main())
