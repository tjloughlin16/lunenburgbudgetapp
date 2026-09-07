#!/usr/bin/env python3
"""Publish the reference pages, which were built and then reachable by nobody.

    python3 scripts/build_reference_pages.py
    python3 scripts/build_reference_pages.py --check

Copies the reference documents out of `notes/reference/` into `fy28/public/reference/`,
byte for byte, and writes `fy28/public/data/reference.json` — the machine-readable index
of what was published, where it now lives, and what produced it.

WHY THIS EXISTS

Self-contained HTML pages and two generated Markdown references sat in
`notes/reference/`, and `notes/reference/data-model/README.md` said out loud what the
consequence was: *"Open them from disk — that is where they live."* They are among the
best material this project has — the whole database table by table, every dollar into the
town and who decides it, what can be joined to what and what never can — and the only
person who could read them had a clone of the repository.

A document nobody can reach is indistinguishable from a document nobody wrote. This is
`notes/plans/SITE-EXPANSION.md` Phase 2, and only the publishing half of it: the files get
stable addresses and an index. Framing them inside the app, putting them behind a door and
naming them in the nav is Phase 2's other half and is deliberately not here, because those
touch the route table and the route table is being rebuilt.

THE ADDRESS: `/reference/<name>.html`, WITH THE EXTENSION, AND WHY

Extensionless (`/reference/schema`) is the prettier form and it is the wrong one here, for
two reasons and only the second is about aesthetics.

  1. **It cannot be verified from this side.** Cloudflare Pages resolves `/foo` from
     `foo.html` by default, so extensionless would *probably* work — and "probably" is the
     word rule 13 exists to catch. If that default is not what this project's Pages
     settings do, `/reference/schema` does not 404: the SPA fallback serves index.html
     with a **200**, so the failure looks exactly like a page that loaded. A file at a
     file address makes no claim about host behaviour at all. `/reference/schema.html` is
     true because the file is there.
  2. **It leaves the good namespace free.** A later phase may want to render these inside
     the app — a real route, the site's chrome, breadcrumbs — and the natural address for
     that is `/reference/<name>`. Taking it now with a static file would put the raw copy
     and the framed copy in a fight over one URL. The file keeps the file address; the app
     can take the clean one whenever somebody builds it.

The published copies are **byte-identical** to the originals. No header is injected, no
link is rewritten. A published copy that differs from the generated original is a
rendering being quoted as the source (rule 13), and every one of these pages already
carries its own `Lunenburg Budget Project` eyebrow, so the header a transform would add is
already in the bytes. The check is therefore a sha256 comparison and nothing softer.

WHAT IS EXCLUDED, AND WHY — THE JUDGEMENT CALL

`notes/reference/data-model/` holds fifteen files. Eight are published, plus the two
Markdown references from `notes/reference/` itself. The seven that are not published are
each named in `EXCLUDED` below with the reason, and `check_unclassified()` refuses to run
if a file in that folder is in neither list — because a page left out by accident and a
page left out on purpose look identical on disk.

Three of the exclusions are one kind of thing:

  `town-report.html`     A records request, itemised. It is a letter to the Town, drafted
                         here. Publishing it would be publishing our own outbox.
  `after-request.html`   The completeness matrix as it *would* look once that request is
                         filled. A projection about a letter that has not been answered.
  `money-flow.html`      Superseded, and worth knowing about: `build_money_flow.py` writes
                         it and `school-money-flow.html` from the same database on every
                         run, under the SAME `<title>`. The older of the two adds an
                         appropriation to nine months of fund actuals and calls the sum
                         "what the school system actually has" — rule 1, on a live page.
                         Only the v2 page ships.

The fourth is `follow-the-money.html`, and this is the one worth arguing.

`follow-the-money.html` is on SITE-EXPANSION.md's move-in list. It should not be, and the
reason it got there is itself instructive: the page a reader wants under that name is
`money-in.html`, whose `<title>` is literally **"Follow The Money"**. Two files, one name,
and the plan named the wrong one. (This generator asserts that no two published pages share
a title, so that particular confusion cannot recur silently.)

On its own merits `follow-the-money.html` fails three ways:

  * **Its headline claim is no longer true.** It says *"The account table has no function
    column. The key is dropped when lunenburg.db is built, so crosswalk is empty and every
    API view is blind to a join the data supports."* `account` has carried `function` and
    `account_string` since 3 September 2026 and `v_function_budget_vs_ledger` does that
    join. The page is a bug report for a bug that was fixed, and unlike every other page
    here nothing regenerates it, so nothing told it.
  * **It is a to-do list about our own pipeline, not about the town's money.** Its central
    section is headed *"What would fix it — and it is not a request to the Town: Load the
    column that is already there."* That is an instruction to a developer. A resident
    reading it learns about `build_db.py`.
  * **It points at data we chose not to read.** It records that
    `fund_1301_cash_journal` carries a `vendor` column and that athletics officials are
    paid as individuals — a note written to stop somebody reading those values. Putting
    that finding on a public page is an advertisement for the thing it was warning about.

The remaining exclusions are `README.md`, `schema.mmd` and `lineage.json` — notes to a
maintainer, and two inputs to pages that are here.

**Two of what ships have no generator at all** — `join-map.html` and `lineage-graph.html`
are hand-written HTML. (`match-matrix.html` is a third case: `build_data_model_grids.py`
regenerates its first grid and nothing regenerates its prose, so it reports a generator
and is only half covered by one.) They ship anyway, because everything they assert is
about the archive's own limits rather than about anybody, and those limits are the most
honest thing this project has to say. But the index records `generators` for every page,
derived by looking for the filename in `scripts/` rather than typed, so "which of these
does a script reproduce" is a published fact and not a claim. The ones with none are the
ones to distrust first — a hand-written page is a page nothing will tell when what it
describes moves underneath it, which is precisely how `follow-the-money.html` came to be
wrong.

WHAT THE INDEX IS FOR

`fy28/public/data/reference.json` exists so that the human index — the door, the nav, the
cards — can be built in a later phase from this file instead of somebody retyping ten
titles into a component. Every title is read from the document itself: the `<title>` for
HTML, the first `# ` heading for Markdown. Rule 2 applies to a page title exactly as it
applies to a figure; a title typed into a nav is wrong the first time a page is renamed
and nothing fails.

The one-line descriptions ARE editorial and are written here rather than derived, on the
same footing as `ABOUT` in `build_reports_index.py`: what a page is *for* is a judgement
about a reader, and no part of the file states it.
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_MODEL = os.path.join(ROOT, 'notes', 'reference', 'data-model')
REFERENCE = os.path.join(ROOT, 'notes', 'reference')
SCRIPTS = os.path.join(ROOT, 'scripts')
PUB = os.path.join(ROOT, 'fy28', 'public', 'reference')
INDEX = os.path.join(ROOT, 'fy28', 'public', 'data', 'reference.json')

# TIER — is this a document a resident should be handed, or one they arrive at after
# asking a second question?
#
# TJ, reading the money page: "follow the money is too low level to be a top doc. its a
# secondary/detailed doc. same with who decides. and the town ledger structure."
#
# He is right, and the distinction is not about quality. The two FLOW diagrams answer the
# question somebody actually walks in with — where does the money come from and where does
# it go — and everything else answers a question you only have once you have seen them:
# which route exactly, who signs, how is the ledger named. Presenting five documents as
# equals makes a reader choose between things that are not alternatives.
#
# `primary` is deliberately scarce. Two per door at most; if a third looks primary, the
# honest move is to ask which of the three a resident would open first and demote the
# other two.
TIER_PRIMARY = 'primary'
TIER_SECONDARY = 'secondary'

# What ships, in the order a reader should meet it, with the door SITE-EXPANSION.md puts
# it behind. Source paths are relative to the repository root -- written out rather than
# globbed, because "which of these is fit to publish" is a decision per file and a glob
# would silently publish the next thing somebody drops in the folder. The exclusions are
# argued in the docstring above; `EXCLUDED` below keeps them from being forgotten.
#
# `about` is editorial. Everything else about a page is read from the page.
PAGES = [
    dict(src='notes/reference/data-model/schema.html', tier=TIER_PRIMARY, door='the data', about=(
        'Every table in the database, what it is for, which years it actually covers — '
        'and, first, whether the question you arrived with can be answered at all.')),
    dict(src='notes/reference/data-model/money-in.html', tier=TIER_SECONDARY, door='the money', about=(
        'Every route into the school budget and out the other side, level by level, and '
        'the level at which each trail goes cold.')),
    dict(src='notes/reference/data-model/school-money-flow.html', tier=TIER_PRIMARY, door='the money', about=(
        'FY2026 drawn end to end: every source the town budgets, the 258 accounts the '
        'school department spends from, and the connection in the middle nobody records.')),
    dict(src='notes/reference/data-model/town-money-flow.html', tier=TIER_PRIMARY, door='the money', about=(
        'The same model applied to all of Lunenburg — the general fund, the enterprise '
        'funds and the special revenue funds, in one picture.')),
    dict(src='notes/reference/data-model/who-decides.html', tier=TIER_SECONDARY, door='the money', about=(
        'Where each dollar comes to rest and who actually gets to decide how it is spent '
        '— the question the budget documents never answer.')),
    dict(src='notes/reference/LEDGER-STRUCTURE.md', tier=TIER_SECONDARY, door='the money', about=(
        'How the town’s ledger is built and named: what an account number means, what a '
        'fund number means, and why a name in it must never be used to identify anything.')),
    dict(src='notes/reference/MONEY-NODES.md', tier=TIER_SECONDARY, door='the data', about=(
        'Every node in the school money graph as a flat list, inputs and outputs, each '
        'marked traced, partial or unknown. The rows with no number are the point.')),
    dict(src='notes/reference/data-model/join-map.html', tier=TIER_SECONDARY, door='the data', about=(
        'Six levels of detail, the key each one turns on, and which of them the district’s '
        'budget and the town’s books can actually be brought together at.')),
    dict(src='notes/reference/data-model/match-matrix.html', tier=TIER_SECONDARY, door='the data', about=(
        'Three levels of the school budget against four things to match them to. Each cell '
        'says what is true today and, separately, what would open it.')),
    dict(src='notes/reference/data-model/lineage-graph.html', tier=TIER_SECONDARY, door='the data', about=(
        'Question to key to table to extract to report, as a graph — and the three '
        'different ways a connection fails, only one of which a schema can show.')),
]

# Named, not merely absent. A file left out of PAGES by accident and a file left out on
# purpose look identical; this is the difference, and `check_unclassified()` below fails
# if a data-model document is in neither list.
EXCLUDED = {
    'notes/reference/data-model/follow-the-money.html':
        'Stale — its headline claim (`account` has no `function` column) was fixed on '
        '3 September 2026 and nothing regenerates the page to notice. It is also a to-do '
        'list for our own build rather than a document about the town’s money, and it '
        'names the vendor data we deliberately chose not to read.',
    'notes/reference/data-model/town-report.html':
        'A records request drafted here, addressed to the Town. Our outbox, not a '
        'reference document.',
    'notes/reference/data-model/after-request.html':
        'A projection of what completeness would look like once that request is filled. '
        'It describes a letter that has not been answered.',
    'notes/reference/data-model/money-flow.html':
        'Superseded. `build_money_flow.py` writes this AND school-money-flow.html from '
        'the same database on every run, and gives them the identical <title>. This is '
        'the older framing — it adds an appropriation to nine months of fund actuals and '
        'calls the sum "what the school system actually has", which is rule 1. The v2 '
        'page beside it separates the bases and is what ships.',
    'notes/reference/data-model/README.md':
        'Notes to whoever maintains the folder, including the paths of the scripts that '
        'build it. Its content is this docstring’s job now.',
    'notes/reference/data-model/schema.mmd':
        'An input to schema.html, not a document.',
    'notes/reference/data-model/lineage.json':
        'An input to lineage-graph.html, not a document.',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def title_of(path):
    """The document's own title. Never typed here — see rule 2.

    HTML gives up its `<title>`; Markdown gives up its first `# ` heading. Both are read
    verbatim, including any ` — Lunenburg Budget Project` suffix a page carries: trimming
    it would be this script deciding what the page is called, which is the whole thing
    being avoided.
    """
    text = open(path, encoding='utf-8').read()
    if path.endswith('.html'):
        m = re.search(r'<title[^>]*>(.*?)</title>', text, re.S | re.I)
        if not m:
            raise SystemExit('%s has no <title>, so its name would have to be typed here.'
                             % os.path.relpath(path, ROOT))
        raw = m.group(1)
    else:
        m = re.search(r'^#\s+(.+)$', text, re.M)
        if not m:
            raise SystemExit('%s has no `# ` heading, so its name would have to be typed '
                             'here.' % os.path.relpath(path, ROOT))
        raw = m.group(1)
    # Entity decoding is deliberately limited to the four that appear, so an entity this
    # does not understand shows up as itself rather than being half-decoded.
    out = re.sub(r'\s+', ' ', raw).strip()
    for ent, ch in (('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&mdash;', '—')):
        out = out.replace(ent, ch)
    return out


def generator_of(name):
    """Which script writes this file, found by looking rather than by being told.

    Grepping `scripts/` for the filename is a weaker test than reading each generator's
    output path, and it is the right weakness: it can name a script that merely mentions
    the file, but it cannot MISS one, and a false `null` here — a page reported as
    hand-written when a generator does exist — is the direction that misleads.
    """
    hits = []
    for f in sorted(os.listdir(SCRIPTS)):
        if not f.endswith('.py') or f == os.path.basename(__file__):
            continue
        with open(os.path.join(SCRIPTS, f), encoding='utf-8', errors='replace') as fh:
            if name in fh.read():
                hits.append('scripts/' + f)
    return hits


def check_unclassified():
    """Every document in the folder is either published or excluded by name.

    The failure this catches is an omission, which is the one shape nothing here finds by
    re-reading: somebody generates a twelfth reference page, it is in neither list, and
    the site goes on serving eleven while being correct about all of them.
    """
    known = {p['src'] for p in PAGES} | set(EXCLUDED)
    stray = []
    for f in sorted(os.listdir(DATA_MODEL)):
        rel = 'notes/reference/data-model/' + f
        if os.path.isfile(os.path.join(DATA_MODEL, f)) and rel not in known:
            stray.append(rel)
    if stray:
        raise SystemExit(
            'Not published and not excluded, so nobody has decided about it:\n  %s\n'
            'Add it to PAGES with a description, or to EXCLUDED with the reason.'
            % '\n  '.join(stray))


def build():
    check_unclassified()
    entries, seen_titles = [], {}
    for page in PAGES:
        src = os.path.join(ROOT, page['src'])
        if not os.path.exists(src):
            raise SystemExit('%s is in PAGES and is not on disk.' % page['src'])
        name = os.path.basename(src)
        title = title_of(src)

        # Two files with one name is exactly how `follow-the-money.html` came to be listed
        # in the plan where `money-in.html` — actual title "Follow The Money" — was meant.
        # A published index that carries the same title twice is unusable as a nav.
        if title in seen_titles:
            raise SystemExit('Two published pages are both titled %r: %s and %s. One of '
                             'them needs renaming at source.'
                             % (title, seen_titles[title], page['src']))
        seen_titles[title] = page['src']

        entries.append(dict(
            name=name,
            title=title,
            about=page['about'],
            door=page['door'],
            tier=page['tier'],
            url='/reference/' + name,
            source=page['src'],
            format='html' if name.endswith('.html') else 'markdown',
            bytes=os.path.getsize(src),
            sha256=sha256(src),
            # null means hand-written: nothing reproduces it, so nothing will notice when
            # what it describes moves underneath it. That is a property a reader is
            # entitled to, and it is derived.
            generators=generator_of(name) or None,
        ))

    return dict(
        about=('Reference documents published from notes/reference/, byte for byte. Each '
               'is self-contained: open it and everything it needs is in the file.'),
        caveat=('Written by this project, not by the town or the district. Every figure '
                'on these pages is computed from sources/data/lunenburg.db or from the '
                'documents in the archive, and a page with no generator listed is '
                'hand-written — its figures were true when it was written and nothing '
                'checks that they still are.'),
        pages=entries,
        excluded=[dict(source=k, reason=v) for k, v in sorted(EXCLUDED.items())],
    )


def main():
    data = build()
    fresh = json.dumps(data, separators=(',', ':'), sort_keys=True, ensure_ascii=False)

    if '--check' in sys.argv:
        # Two things are checked and they fail differently on purpose.
        #
        # 1. The INDEX still reproduces. Catches a page added, removed, renamed or
        #    retitled at source without being republished.
        # 2. Every published FILE still hashes to what its source hashes to. Catches the
        #    ordinary case — a generator re-ran, the original changed, the copy did not.
        #
        # Nothing volatile is in the comparison. There is deliberately no `generated`
        # date: `build_reports_index.py` puts `date.today()` inside the text it compares,
        # which means its --check passes on the day it was run and would fail on the next
        # one for no reason at all. A check that cries wolf gets ignored on the day it is
        # right.
        problems = []
        if not os.path.exists(INDEX):
            raise SystemExit('%s does not exist. Run without --check.'
                             % os.path.relpath(INDEX, ROOT))
        current = open(INDEX, encoding='utf-8').read()
        if current != fresh:
            was = {p['name'] for p in json.loads(current).get('pages', [])}
            has = {p['name'] for p in data['pages']}
            problems.append(
                'STALE: %s no longer reproduces.%s%s'
                % (os.path.relpath(INDEX, ROOT),
                   '\n  the index is MISSING: %s' % ', '.join(sorted(has - was))
                   if has - was else '',
                   '\n  the index lists what is gone: %s' % ', '.join(sorted(was - has))
                   if was - has else ''))

        for p in data['pages']:
            dest = os.path.join(PUB, p['name'])
            if not os.path.exists(dest):
                problems.append('NOT PUBLISHED: %s (%s)' % (p['url'], p['source']))
            elif sha256(dest) != p['sha256']:
                problems.append('DRIFTED: %s no longer matches %s' % (p['url'], p['source']))

        # Anything in the published folder that is not in PAGES. An excluded page that
        # got copied once and stayed is served forever and appears in no index.
        if os.path.isdir(PUB):
            expected = {p['name'] for p in data['pages']}
            for f in sorted(os.listdir(PUB)):
                if f not in expected:
                    problems.append('ORPHAN: fy28/public/reference/%s is published and is '
                                    'in no index' % f)

        if problems:
            raise SystemExit('\n'.join(problems) + '\n  Run: python3 '
                             'scripts/build_reference_pages.py')
        print('ok: %d reference pages published, each identical to its source'
              % len(data['pages']))
        return 0

    os.makedirs(PUB, exist_ok=True)
    for p in data['pages']:
        with open(os.path.join(ROOT, p['source']), 'rb') as fh:
            blob = fh.read()
        with open(os.path.join(PUB, p['name']), 'wb') as fh:
            fh.write(blob)

    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    with open(INDEX, 'w', encoding='utf-8') as fh:
        fh.write(fresh)

    print('wrote %d files to %s' % (len(data['pages']), os.path.relpath(PUB, ROOT)))
    for p in data['pages']:
        print('  %-28s %-9s %s' % (p['url'], p['door'],
                                   '' if p['generators'] else 'HAND-WRITTEN'))
    print('wrote %s' % os.path.relpath(INDEX, ROOT))
    print('  %d excluded, each with its reason: %s'
          % (len(data['excluded']), ', '.join(os.path.basename(e['source'])
                                              for e in data['excluded'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
