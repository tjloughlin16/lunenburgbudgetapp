"""Publish the index of analyses this project has written.

    python3 scripts/build_reports_index.py

Writes `fy28/public/data/reports.json`, which the /reports page renders.

TWO KINDS OF ANALYSIS, AND FOR MONTHS THIS SAW ONLY ONE

Every analysis used to be a Markdown document, so scanning `sources/analyses/` scanned
everything and the comment on `AREA_HOME` in routes.ts could say /reports "is the generated
index of every analysis on disk". Then eight analyses were built as React pages in a single
day, and the sentence stopped being true without anything failing: /reports is the front
door of the whole Analyses area and it listed the documents and none of the pages.

So this reads BOTH, and from the tables that decide them rather than from a list kept
beside them:

  - the DOCUMENTS from `sources/analyses/*.md`, as before;
  - the PAGES from `AREA_TABS.analyses` in `fy28/src/routes.ts` -- the same table the app's
    own navigation is drawn from -- joined to the page component that declares that tab.

`--check` fails if either goes missing, which is the promise that comment was making.

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
import glob
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
    'fy27-and-the-override', 'fy27-cut-reconciliation', 'per-pupil-spending',
    'peer-districts',
    'connecting-the-budget', 'show-your-work',
]

# --- how a READER groups these, which is not how we built them ----------------------
#
# The index was split into "routed reports" and "written analyses", which is a fact about
# our implementation and nothing a resident cares about. It also DUPLICATED subjects:
# Monty Tech appeared twice and special education three times, because each has both a
# page and a document. TJ, seeing it: "monty tech being in the 'written' section seems
# wrong. I think a breakdown of school vs town to start is good, then subcategories
# might help."
#
# So: grouped by SUBJECT, and one entry per subject. Where a page and a document cover
# the same ground the PAGE wins and the document is offered from it, because the page is
# current, computed on every build, and the document is what it was written from.
#
# SCHOOL first because that is where the money and the argument are; TOWN second; METHOD
# last, for the reader who has a reason to check rather than a question to answer.
CATEGORIES = [
    ('school', 'The schools', [
        ('what the money buys', [
            'sped', 'courses', 'cuts', 'sportsmoney', 'stopped', 'unwind',
            'insurance',
            'athletics-ledger',
        ]),
        # TJ, 10 September 2026: this belongs "under The Schools, and just above 'the
        # students'". It had been a top-level shelf of its own, and the correction is
        # right for a reason the shelf version missed: a reader browsing the schools is
        # already in the place where "who works in them" is the obvious next question.
        # A top-level shelf made it a peer of "The town", which it is not — it is one
        # aspect of the schools, and the order adults-then-children reads the way a
        # person would ask it.
        ('who works in them', [
            'staffing', 'schoolstaff', 'parastaff',
        ]),
        ('the students', [
            'attrition', 'outflow', 'montytech', 'leaving', 'families',
        ]),
        ('where the money comes from, and how it compares', [
            'minaid', 'required', 'peers', 'variance',
        ]),
    ]),
    ('town', 'The town', [
        ('the ledger, read', [
            'fy26-closeout', 'fy26-closeout-town', 'free-cash',
        ]),
        ('what the votes decided', [
            'fy27-and-the-override', 'fy27-cut-reconciliation',
        ]),
    ]),
    # A FOURTH SHELF, AND THE ARGUMENT FOR IT.
    #
    # The first three answer "is this about the schools, the town, or how to check it",
    # and every report fits one because every report MEASURES Lunenburg. The class-size
    # rule does not. It quotes a state regulation that binds every district in
    # Massachusetts, and its whole discipline is that it stops before saying anything
    # about this town's staffing -- so filing it under "the schools / what the money buys"
    # would promise a Lunenburg finding the page deliberately refuses to make, and a
    # reader who opened it expecting one would leave thinking the page had failed.
    #
    # TJ asked for a new section and this is why one is right rather than merely asked
    # for: a rule everybody argues under is a different KIND of document from a
    # measurement, and the index is the one place a reader learns which they are getting.
    #
    # The shelf is expected to fill. Chapter 70's formula, the net school spending
    # requirement and Proposition 2 1/2's levy limit are all rules this town argues under
    # and all currently sit under headings about where money comes from -- which is right
    # for them TODAY, because each of those pages measures Lunenburg against the rule.
    # Nothing is moved here: an address that has been shared once keeps landing where it
    # landed, and a category is not a reason to move a page.
    # `formula` is the second entry on this shelf and it is the case the note above
    # forecast. It explains Chapter 70 — a statute that binds every district in
    # Massachusetts — in eight plain steps, and its discipline is that it stops at the
    # mechanism. `minaid` stays under "where the money comes from" because that page
    # MEASURES Lunenburg against the rule; this one explains the rule. Two pages, two
    # shelves, and neither is moved.
    ('rules', 'The rules everyone argues under', [
        ('', ['classsize', 'formula']),
    ]),
    ('method', 'How to check any of it', [
        ('', ['connecting-the-budget', 'what-you-can-ask', 'questions']),
    ]),
]

# A page and a document covering the same subject. The page is what the index offers.
SUPERSEDED = {
    'monty-tech': 'montytech',
    'sped-and-the-curve': 'sped',
    'sped-and-funds': 'sped',
    'per-pupil-spending': 'peers',
    'peer-districts': 'peers',
    'athletics': 'sportsmoney',
    'budget-vs-actual': 'variance',
}

# `show-your-work` is deliberately in no category: the page gives it a section of its own,
# last, because it is the document that makes every figure on every other report checkable
# rather than another report about money.
#
# `addsup` (/what-it-all-adds-up-to) is likewise outside the grouping, at the other end:
# it is the synthesis of what every other report concludes, so it belongs ABOVE the
# categories rather than inside one. The page renders it first and on its own.
UNCATEGORISED = {'show-your-work', 'addsup'}

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
    'monty-tech':
        'The larger of the two routes out of Lunenburg’s own schools, and the only school '
        'line the town cannot vote on. What sets the assessment, why 95% of it is a figure '
        'the state calculates, and which parts of the twenty-year series are established.',
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
    'per-pupil-spending':
        'What DESE says Lunenburg spends for each pupil, against every district in '
        'Massachusetts and against five neighbours — and the arithmetic that says how '
        'much of the difference is money and how much is children.',
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


ROUTES_TS = os.path.join(ROOT, 'fy28', 'src', 'routes.ts')
PAGES_DIR = os.path.join(ROOT, 'fy28', 'src', 'pages')
DATA_DIR = os.path.join(ROOT, 'fy28', 'public', 'data')

# One line on what each ROUTED report answers, for the pages whose payload does not carry
# an `about` of its own. Editorial, so written here rather than derived -- and the build
# prints which pages fell back to their own title, so a new page is visible rather than
# silently described by nothing.
ABOUT_PAGES = {
    'sportsmoney':
        'Athletics with both sides of the money visible at once — the town’s '
        'appropriation, the fee-funded revolving fund, and three district documents that '
        'state three different costs for the same team in the same year.',
    'variance':
        'What the district budgeted against what it later reported spending, line by '
        'line — and why nothing before FY2026 is an accounting record.',
    'insurance':
        'School health insurance that is appropriated to a department which is not the '
        'schools, with the account number on it.',
    'leaving':
        'What it would cost the town if more children left under school choice — a '
        'scenario with dials, priced against DESE’s own counts.',
    'staffing':
        'Whether school staffing went up, over any span of years you choose — with the '
        'four quantities the archive holds kept apart: names the town printed, FTE and '
        'headcount the state published, and dollars.',
    'attrition':
        'Which grades Lunenburg children leave in, seventeen years of it — one '
        'grade does almost all of it, and no published record says where any of them '
        'went.',
    'courses':
        'How many classes actually ran in each subject at the high school, year by '
        'year — the one measure here of what was taught rather than who was '
        'employed to teach it.',
    'stopped':
        'Every time a school budget line went to a printed zero, and how many of them '
        'came back.',
    'cuts':
        'Every reduction the district named in its own budget documents, cycle by cycle, '
        'quoted at its page — and, where a state series reaches it, whether the count '
        'moved with it.',
    'funds':
        'The money the town holds and spends outside the budget Town Meeting votes — '
        'grants, revolving funds, gifts and the enterprise funds.',
    'stateaid':
        'The share of the school budget that arrives from the State House, and the '
        'difference between Chapter 70 and total state aid.',
    'families':
        'Every school fee a Lunenburg household can be charged, priced for one to four '
        'children, and the three places the published record runs out.',
    'sped':
        'Four special education reports behind one door, and the reason they must not be '
        'combined: each counts a different thing.',
    # NOT `classsize`. Its payload carries its own `about`, which wins here -- and a
    # second description of the same page in this file is the artefact that goes stale
    # first. The generated one is the one the index prints.
}


def analyses_area_tabs():
    """Every tab the app files in the ANALYSES area, whether or not it is in the bar.

    `AREA_TABS.analyses` is the bar, and the bar is deliberately shorter than the area:
    the four special education reports sit behind one `sped` entry because a bar with
    fourteen entries is a sitemap. `AREA_OF` is the full membership, and anything that
    means to cover the area rather than the bar has to read this one --
    /what-it-all-adds-up-to does, which is how it reaches
    /what-special-education-costs at all.
    """
    src = open(ROUTES_TS, encoding='utf-8').read()
    m = re.search(r'const AREA_OF: Partial<Record<Tab, Area>> = \{(.*?)\n\}', src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find the AREA_OF table')
    tabs = [t for t, a in re.findall(r"(\w+): '(\w+)'", m.group(1)) if a == 'analyses']
    # `analysis` is the ONE tab that renders all seventeen Markdown documents at
    # /analysis/<id>. It owns no single report, declares no `const TAB`, and has no
    # payload, so it is not a row anywhere reports are enumerated.
    tabs = [t for t in tabs if t != 'analysis']
    if not tabs:
        raise SystemExit('routes.ts: AREA_OF names no analyses tabs, which has never '
                         'been true')
    return tabs


def parents():
    """`PARENT` in routes.ts: which page a drill-in sits under.

    Used for ORDERING here, not for navigation. It is the table that already records
    which door each hidden report is behind, so reading it is how the master report can
    place the four special education reports where the bar puts special education without
    anybody keeping a second list in step with the first.
    """
    src = open(ROUTES_TS, encoding='utf-8').read()
    m = re.search(r'export const PARENT: Partial<Record<Tab, Tab>> = \{(.*?)\n\}',
                  src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find the PARENT table')
    out = dict(re.findall(r"(\w+): '(\w+)'", m.group(1)))
    if not out:
        raise SystemExit('routes.ts: the PARENT table parsed to nothing')
    return out


def routed_reports(all_of_area=False):
    """Every report the app routes to, read off the table the app itself routes on.

    `all_of_area=True` covers the whole Analyses AREA rather than its tab bar -- see
    `analyses_area_tabs`. The bar is the default because /reports is a navigation index
    and the bar is what a reader navigates.

    `AREA_TABS.analyses` in routes.ts is the Analyses area's own tab list. Parsed rather
    than imported, for the same reason `prerender.mjs` parses it: this is a TypeScript file
    and we are running plain Python. The parse asserts what it found, because a regex that
    matches nothing looks exactly like an area with no reports in it.
    """
    src = open(ROUTES_TS, encoding='utf-8').read()

    m = re.search(r'^\s*analyses: \[(.*?)\],\n', src, re.S | re.M)
    if not m:
        raise SystemExit('routes.ts: could not find AREA_TABS.analyses')
    tabs = re.findall(r"'([a-z]+)'", m.group(1))
    if not tabs:
        raise SystemExit('routes.ts: AREA_TABS.analyses parsed to nothing')
    if all_of_area:
        # THE BAR'S ORDER, WITH EACH HIDDEN REPORT PUT WHERE ITS DOOR IS.
        #
        # The bar draws `sped` -- one entry for four reports -- and the four are not in it.
        # Appending them produced a page that ended on special education, which is the
        # subject this town argues about most; the bar itself says where that subject
        # sits, second, and `PARENT` in routes.ts says which door each of the four is
        # behind. So each report the bar does not draw is inserted directly after its
        # parent rather than at the end. Both facts are read off routes.ts: the ordering
        # decision stays where the ordering decisions already are.
        parent = parents()
        for t in analyses_area_tabs():
            if t in tabs:
                continue
            pt = parent.get(t)
            at = tabs.index(pt) + 1 if pt in tabs else len(tabs)
            # ...and successive children keep their own order rather than reversing.
            while at < len(tabs) and parent.get(tabs[at]) == pt:
                at += 1
            tabs.insert(at, t)

    block = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    slug = dict(re.findall(r"^\s*(\w+): '([^']*)',", block.group(1), re.M))
    lab = re.search(r'export const LABEL: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not lab:
        raise SystemExit('routes.ts: could not find the LABEL table')
    label = dict(re.findall(r"^\s*(\w+): '(.*?)',$", lab.group(1), re.M))

    # tab -> the page component that declares it, and the payload it draws.
    owner, payload = {}, {}
    for f in sorted(os.listdir(PAGES_DIR)):
        if not f.endswith('.tsx'):
            continue
        text = open(os.path.join(PAGES_DIR, f), encoding='utf-8').read()
        t = re.search(r"^const TAB: Tab = '([a-z]+)'", text, re.M)
        if not t:
            continue
        owner[t.group(1)] = 'fy28/src/pages/' + f
        d = (re.search(r"^const DATA = '/data/([^']+)'", text, re.M)
             or re.search(r"useReport<[^>]*>\('([^']+)'\)", text))
        if d:
            payload[t.group(1)] = d.group(1)

    missing = [t for t in tabs if t != 'reports' and t not in owner]
    if missing:
        raise SystemExit(
            'These reports are routed in AREA_TABS.analyses and no page component claims '
            'them:\n  %s\nEvery report page declares `const TAB: Tab = ...` so this index '
            'cannot silently omit it.' % ', '.join(missing))

    out, undescribed = [], []
    for t in tabs:
        if t == 'reports':      # the index itself is not a row in the index
            continue
        about = ABOUT_PAGES.get(t)
        data = None
        if t in payload:
            fp = os.path.join(DATA_DIR, payload[t])
            if os.path.exists(fp):
                data = dict(url='/data/' + payload[t], bytes=os.path.getsize(fp),
                            sha256=sha256(fp))
                # Prefer the payload's OWN description where it carries one: it is written
                # by the generator that computes the figures, so it cannot describe a
                # report the data no longer supports.
                try:
                    about = json.load(open(fp, encoding='utf-8')).get('about') or about
                except (ValueError, OSError):
                    pass
        if not about:
            undescribed.append(t)
        out.append(dict(
            id=t, kind='page', title=label.get(t, t), url='/' + slug[t],
            about=about or label.get(t, t), component=owner[t],
            data=data, generator=generator_for(payload.get(t))))
    return out, undescribed


def generator_for(payload_name):
    """The script that writes a page's payload, found by looking for it.

    Derived rather than tabulated: /reports promises a reader the script that recomputes
    every figure, and a hand-kept mapping from page to script is the thing that goes stale
    the first time one is renamed.
    """
    if not payload_name:
        return None
    hits = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'scripts', 'build_*.py'))):
        with open(p, encoding='utf-8') as fh:
            if payload_name in fh.read():
                hits.append('scripts/' + os.path.basename(p))
    return hits[0] if len(hits) == 1 else (hits[0] if hits else None)


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
            id=n, kind='document', title=title,
            # The document, rendered on the site in the same shell as every other report.
            # The .md stays the source of truth and stays published -- rule 12 -- and the
            # page renders it rather than transcribing it. See fy28/src/pages/Analysis.tsx.
            url=f'/analysis/{n}',
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

    pages, undescribed = routed_reports()

    # --- group by subject, one entry per subject ------------------------------------
    by_id = {r['id']: r for r in list(reports) + list(pages)}
    groups, placed = [], set()
    for key, title, subs in CATEGORIES:
        out_subs = []
        for sub_title, ids in subs:
            rows = []
            for i in ids:
                if i in by_id:
                    rows.append(i)
                    placed.add(i)
            if rows:
                out_subs.append(dict(title=sub_title, ids=rows))
        if out_subs:
            groups.append(dict(key=key, title=title, sections=out_subs))

    # AND THE SECOND TAXONOMY MUST COVER THE SAME REPORTS. `/what-it-all-adds-up-to`
    # groups the same set by SUBJECT rather than by school/town, because special education
    # is four reports the index draws behind one door and athletics is two the index
    # separates -- see `conclusions.TOPICS`, which is the only declaration of it. Two
    # groupings over one set will drift unless something compares them, and a reader who
    # meets special education under one heading here and another there learns that neither
    # is meaningful. So this refuses to write if a routed report is in neither.
    import conclusions as _C
    astray = sorted(p['id'] for p in pages
                    if p['id'] not in _C.NOT_A_REPORT and not _C.topic_of(p['id']))
    if astray:
        raise SystemExit(
            'these routed reports are in no subject in conclusions.TOPICS, so '
            '/what-it-all-adds-up-to would not show them: %s\nAdd each to a topic there, '
            'or to NOT_A_REPORT if it is not a report.' % ', '.join(astray))

    # NOTHING MAY FALL OUT OF THE TAXONOMY SILENTLY. A report that is in neither a
    # category, nor superseded by one, nor deliberately uncategorised would simply stop
    # being listed -- the failure this index exists to prevent, arriving through the
    # feature meant to organise it. So it refuses to write.
    unplaced = sorted(set(by_id) - placed - set(SUPERSEDED) - UNCATEGORISED)
    if unplaced:
        raise SystemExit(
            'these reports are in no category:\n  ' + '\n  '.join(unplaced) +
            '\n\nAdd each to CATEGORIES in this script, or to SUPERSEDED if a page '
            'already covers the same subject, or to UNCATEGORISED if it genuinely '
            'belongs outside the grouping. Nothing written.')

    # And a supersession must point at something that exists, or the document it hides
    # would vanish while the page it points to was never built.
    missing = sorted(v for v in SUPERSEDED.values() if v not in by_id)
    if missing:
        raise SystemExit('SUPERSEDED points at reports that do not exist: %s. '
                         'Nothing written.' % missing)

    data = dict(
        generated=date.today().isoformat(),
        groups=groups,
        superseded={k: v for k, v in SUPERSEDED.items() if k in by_id},
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
        # The reports that are React PAGES rather than documents. Same area, same shell,
        # same print stylesheet; what differs is that a page is computed from a published
        # payload on every build and a document is prose with a verifier beside it.
        pages=pages,
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
            was = ({r['id'] for r in now.get('reports', [])}
                   | {r['id'] for r in now.get('pages', [])})
            has = ({r['id'] for r in data['reports']}
                   | {r['id'] for r in data['pages']})
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
        print('ok: %s lists all %d documents and all %d routed reports'
              % (os.path.relpath(OUT, ROOT), len(data['reports']), len(data['pages'])))
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d documents, %d with a verifier, %d with a PDF'
          % (len(reports), sum(1 for r in reports if r['verifier']),
             sum(1 for r in reports if r['pdf'])))
    print('  %d routed reports, %d with a published payload, %d with a named generator'
          % (len(pages), sum(1 for r in pages if r['data']),
             sum(1 for r in pages if r['generator'])))
    if undescribed:
        print('  NOT described in ABOUT_PAGES and carrying no `about` in their payload, '
              'showing their own title instead: %s' % ', '.join(undescribed))
    if unlisted:
        print('  NOT described in ABOUT, showing their own opening instead: %s'
              % ', '.join(unlisted))
    return 0


if __name__ == '__main__':
    sys.exit(main())
