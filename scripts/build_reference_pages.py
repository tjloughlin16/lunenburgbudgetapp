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

THE BAR, AND WHAT IT COST TO ADD IT

These pages were published byte-identical, and that was right until they were linked. A
reader who taps `School Money Flow` from the front page leaves the app: no header, no nav,
and **no way back** except the browser button. The database door on the front page opens
`/reference/schema.html` directly, so for many visitors that stranded page is the FIRST
page of this project they see.

So one element is now injected into every published HTML page, immediately before its
`<div class="wrap">`: the project wordmark linking to `/`, and the area the document
belongs to. `door` on each page below says which area. `the money` links to `/the-money`,
which is a real page. `the data` does NOT link, and that is deliberate — the data area has
no index; `AREA_HOME.data` is the rate register, which is a document about athletic fees
and a baffling destination for somebody leaving the schema page, and linking it to `/`
would land a reader on a chooser whose only data door is the page they just left. A label
that is not a link is better than a link that goes in a circle.

The bar carries its own `<style>`, injected after every stylesheet the page already has,
and every property in it is stated literally. It reads none of the page's custom
properties — `--ink` means eight different colours across these eight documents — and it
sets its own font, colour and link decoration rather than inheriting them, so a page rule
like `a { border-bottom: none }` cannot reach it. Its palette is defined for light and
flipped under `prefers-color-scheme: dark`, matching what each page does for itself. It is
NOT sticky: `schema.html` has a `position:fixed` modal at `z-index:9` and sticky table
headers at `top:0`, and a second sticky element at the top of the viewport would fight
both.

WHY THE TWO MARKDOWN FILES ARE NOT TRANSFORMED, AND WHAT THEY GET INSTEAD

`LEDGER-STRUCTURE.md` and `MONEY-NODES.md` are Markdown. Injecting HTML into them would
corrupt them as documents — a `<div>` in a `.md` file is not markup a Markdown reader
renders away, and downloading the file is a real use of it (rule 12: our processed copy,
downloadable). So the `.md` copies stay **byte-identical to their sources, permanently**.

Each also gets a sibling `.html` at the same stem — `/reference/LEDGER-STRUCTURE.html` —
which carries the bar, the document's own title, a link to the raw `.md`, and the
Markdown **verbatim inside a `<pre>`**. The index points `url` at the HTML, so the front
page links a reader to a page with a way back, and `raw` at the `.md`, so the document
itself is still one fetch away.

The `<pre>` is the argument worth stating. The alternative is a Markdown-to-HTML renderer
written here, and that is precisely the instrument rule 13 is about: something that
reformats the document before anybody sees it, whose output is then quoted as the
document. A `<pre>` cannot mis-render a table, drop an emphasis marker or swallow a pipe.
What a reader sees is what the file says, character for character, which is also what they
get if they follow the raw link. The cost is that a Markdown table is shown as a Markdown
table rather than as a grid, and that is a cost worth paying for a document whose whole
subject is what the data does and does not support.

WHAT `--check` PROVES NOW, AND WHAT IT NO LONGER PROVES

It used to prove one thing very cleanly: **the published file is byte-identical to the
source document.** That is gone, and pretending otherwise would be the exact defect this
file's own docstring warns about.

What it proves instead: **the published file is exactly what `render()` produces from the
current source.** The transform is a pure function of the source bytes, the `door`, and
the constants in this module — no clock, no environment, no ordering that depends on the
filesystem — so the check recomputes every published byte and compares. A source that
changed, a transform that changed, a bar whose link moved, and a published file edited by
hand all fail identically, and they should.

What it does NOT prove any more, and no check here can: that the injected bar is the only
difference between a published page and its source. The transform is the thing asserting
that, and the transform is thirty lines that insert one element before a known anchor and
change nothing else. `sha256` in the index is still the SOURCE document's hash, so a
reader who wants the untouched original can verify it against `notes/reference/`;
`published` carries the hash of each byte actually served.

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


# --- THE BAR -----------------------------------------------------------------------

# The wordmark, and where each `door` goes back to.
#
# Typed here rather than parsed out of `fy28/src/routes.ts`. Reading the label out of the
# route table would be the rule-2 move and it buys a worse property than it costs: this
# generator would then fail — and `check_generated.py` with it — every time somebody has a
# TypeScript file half-edited. `door` is already typed in PAGES above, so the coupling
# exists either way; this keeps it in one file.
#
# Mirrors `AREA_LABEL` and `SLUG` in fy28/src/routes.ts. `None` means the area has no
# index page, and the label is then rendered as plain text — see the docstring.
WORDMARK = 'The Lunenburg Budget Project'
AREAS = {
    'the money': ('The money', '/the-money'),
    'the data': ('The database', None),
}

# Every value literal. Nothing here reads a custom property from the page it lands in:
# `--ink` is a different colour in each of these eight documents, and a bar that borrows
# one is a bar that changes when a page's palette does.
BAR_CSS = """\
/* Injected by scripts/build_reference_pages.py. Not part of the source document. */
.lbp-bar{display:block;margin:0;padding:0;background:#f1eee8;
  border-bottom:1px solid #dcd7ce;color:#5f5a51;
  font:500 13px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
    Helvetica,Arial,sans-serif;letter-spacing:0;text-transform:none}
.lbp-bar .lbp-in{max-width:1180px;margin:0 auto;padding:10px 16px;
  display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.lbp-bar a{font:inherit;color:#1b1a18;text-decoration:none;
  border-bottom:1px solid rgba(0,0,0,.25);padding:0;background:none}
.lbp-bar a:hover{border-bottom-color:currentColor}
.lbp-bar .lbp-mark{font-weight:700}
.lbp-bar .lbp-sep{color:#a29b90}
.lbp-bar .lbp-area{color:#5f5a51}
@media (prefers-color-scheme:dark){
  .lbp-bar{background:#1f1e1b;border-bottom-color:#35322d;color:#a49e94}
  .lbp-bar a{color:#efece7;border-bottom-color:rgba(255,255,255,.28)}
  .lbp-bar .lbp-sep{color:#6f6a61}
  .lbp-bar .lbp-area{color:#a49e94}
}
"""


def esc(s):
    """The four characters that would otherwise stop being text."""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))


def bar(door):
    """The bar, as a `<style>` and one element. A pure function of `door`."""
    if door not in AREAS:
        raise SystemExit('door %r has no area in AREAS, so the bar would have nowhere to '
                         'point.' % door)
    label, href = AREAS[door]
    back = ('<a class="lbp-back" href="%s">%s &rarr;</a>' % (esc(href), esc(label))
            if href else '<span class="lbp-area">%s</span>' % esc(label))
    return ('<style>\n%s</style>\n'
            '<div class="lbp-bar"><div class="lbp-in">'
            '<a class="lbp-mark" href="/">%s</a>'
            '<span class="lbp-sep">&middot;</span>%s'
            '</div></div>\n' % (BAR_CSS, esc(WORDMARK), back))


# The anchor. Every published HTML document opens its body with exactly this, and the
# injection goes immediately before it — after every `<style>` the page carries, so the
# bar's rules are last and win any tie. None of these documents has a `<body>` tag, so
# there is no body boundary to insert at; if a page ever stops using this wrapper, this
# fails loudly rather than guessing.
WRAP = '<div class="wrap">'

# The shell for a Markdown document: the bar, the document's own title, the raw file one
# tap away, and the Markdown verbatim. See the docstring for why it is a `<pre>`.
MD_SHELL = """\
<meta charset="utf-8">
<title>%(title)s</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#fbfaf8;--card:#fff;--ink:#191919;--muted:#6b6b6b;--grid:#e2ded7}
@media (prefers-color-scheme:dark){
  :root{--bg:#141412;--card:#1c1b19;--ink:#eeebe6;--muted:#a09b93;--grid:#34322e}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100%%}
.wrap{max-width:1180px;margin:0 auto;padding:22px 16px 80px}
header{border-bottom:2px solid var(--ink);padding-bottom:14px}
.kicker{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-size:25px;line-height:1.15;margin:8px 0 0;letter-spacing:-.02em}
.note{font-size:13.5px;color:var(--muted);margin:14px 0 0;max-width:70ch}
.note a{color:inherit}
pre.doc{background:var(--card);border:1px solid var(--grid);border-radius:10px;
  padding:16px 15px;margin:18px 0 0;overflow-x:auto;
  font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  white-space:pre;tab-size:2}
%(bar_css)s</style>
%(bar)s<div class="wrap">
<header>
  <p class="kicker">Lunenburg Budget Project &middot; Reference</p>
  <h1>%(title)s</h1>
</header>
<p class="note">This document is written and generated as Markdown. It is shown below
exactly as the file reads &mdash; nothing has re-rendered it &mdash; so what you see is
character for character what you get from
<a href="%(raw)s"><code>%(raw)s</code></a>, which is byte-identical to
<code>%(source)s</code> in the repository.</p>
<pre class="doc">%(body)s</pre>
</div>
"""


def render(source_text, page):
    """Every byte published for one source document, as {filename: bytes}.

    A PURE FUNCTION of the source text and the page's own fields. No clock, no
    environment, no filesystem order. That is the whole basis of `--check`: it can
    recompute this and compare, so a published file is verified to be exactly what the
    current source produces rather than merely verified to exist.
    """
    name = os.path.basename(page['src'])
    if name.endswith('.html'):
        if WRAP not in source_text:
            raise SystemExit('%s does not contain %s, which is where the bar goes. Either '
                             'the page changed shape or it needs a different anchor.'
                             % (page['src'], WRAP))
        head, sep, tail = source_text.partition(WRAP)
        return {name: (head + bar(page['door']) + sep + tail).encode('utf-8')}

    # Markdown: the file itself goes out untouched, and a sibling HTML carries the bar.
    stem = name.rsplit('.', 1)[0]
    raw = '/reference/' + name
    shell = MD_SHELL % dict(
        title=esc(title_of_text(source_text, name)),
        bar_css=BAR_CSS,
        bar=bar(page['door']),
        raw=esc(raw),
        source=esc(page['src']),
        body=esc(source_text))
    return {name: source_text.encode('utf-8'), stem + '.html': shell.encode('utf-8')}


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
    return title_of_text(open(path, encoding='utf-8').read(), path)


def title_of_text(text, path):
    """`title_of`, on text already in hand. Same rules; `path` only names the failure."""
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
    """The index, and every byte that gets published, computed together.

    Returns `(index, files)` — `files` maps a published filename to its exact bytes, so
    the writing half and the checking half cannot disagree about what should be there.
    """
    check_unclassified()
    entries, files, seen_titles = [], {}, {}
    for page in PAGES:
        src = os.path.join(ROOT, page['src'])
        if not os.path.exists(src):
            raise SystemExit('%s is in PAGES and is not on disk.' % page['src'])
        name = os.path.basename(src)
        text = open(src, encoding='utf-8').read()
        title = title_of_text(text, src)

        # Two files with one name is exactly how `follow-the-money.html` came to be listed
        # in the plan where `money-in.html` — actual title "Follow The Money" — was meant.
        # A published index that carries the same title twice is unusable as a nav.
        if title in seen_titles:
            raise SystemExit('Two published pages are both titled %r: %s and %s. One of '
                             'them needs renaming at source.'
                             % (title, seen_titles[title], page['src']))
        seen_titles[title] = page['src']

        rendered = render(text, page)
        for fname, blob in rendered.items():
            if fname in files:
                raise SystemExit('Two sources both publish %s.' % fname)
            files[fname] = blob

        # `url` is the READING address and `raw`, where they differ, is the document
        # itself. For Markdown they differ on purpose: the `.md` cannot carry a way back
        # without ceasing to be Markdown, so the HTML sibling is what a reader is sent to.
        html_name = name if name.endswith('.html') else name.rsplit('.', 1)[0] + '.html'
        entries.append(dict(
            name=name,
            title=title,
            about=page['about'],
            door=page['door'],
            tier=page['tier'],
            url='/reference/' + html_name,
            raw=('/reference/' + name) if html_name != name else None,
            source=page['src'],
            format='html' if name.endswith('.html') else 'markdown',
            bytes=os.path.getsize(src),
            # The SOURCE document's hash, unchanged in meaning: it is what a reader checks
            # the published page against when they want the untouched original.
            sha256=sha256(src),
            # What is actually served, per file. Derived from `render`, so it moves when
            # either the source or the transform does.
            published={f: hashlib.sha256(b).hexdigest()
                       for f, b in sorted(rendered.items())},
            # null means hand-written: nothing reproduces it, so nothing will notice when
            # what it describes moves underneath it. That is a property a reader is
            # entitled to, and it is derived.
            generators=generator_of(name) or None,
        ))

    index = dict(
        about=('Reference documents published from notes/reference/. Each is '
               'self-contained: open it and everything it needs is in the file. The only '
               'edit is a bar at the top linking back into the site — see '
               'scripts/build_reference_pages.py. Markdown documents are published '
               'untouched at `raw` and rendered verbatim, inside a <pre>, at `url`.'),
        caveat=('Written by this project, not by the town or the district. Every figure '
                'on these pages is computed from sources/data/lunenburg.db or from the '
                'documents in the archive, and a page with no generator listed is '
                'hand-written — its figures were true when it was written and nothing '
                'checks that they still are.'),
        pages=entries,
        excluded=[dict(source=k, reason=v) for k, v in sorted(EXCLUDED.items())],
    )
    return index, files


def main():
    data, files = build()
    fresh = json.dumps(data, separators=(',', ':'), sort_keys=True, ensure_ascii=False)

    if '--check' in sys.argv:
        # Three things are checked and they fail differently on purpose.
        #
        # 1. The INDEX still reproduces. Catches a page added, removed, renamed or
        #    retitled at source without being republished.
        # 2. Every published FILE is byte-for-byte what `render()` produces from the
        #    current source. This is the guarantee that replaced "identical to its
        #    source" when the bar started being injected: the transform is pure, so the
        #    check recomputes it rather than trusting a recorded hash. A source that
        #    moved, a transform that changed, a link in the bar that moved, and a hand
        #    edit to a published file all fail here.
        # 3. Nothing else is in the folder. An excluded page copied once and left behind
        #    is served forever and appears in no index.
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

        source_of = {f: p['source'] for p in data['pages'] for f in p['published']}
        for fname in sorted(files):
            dest = os.path.join(PUB, fname)
            if not os.path.exists(dest):
                problems.append('NOT PUBLISHED: /reference/%s (%s)'
                                % (fname, source_of[fname]))
                continue
            with open(dest, 'rb') as fh:
                on_disk = fh.read()
            if on_disk != files[fname]:
                problems.append(
                    'DRIFTED: /reference/%s is not what this script now produces from %s'
                    % (fname, source_of[fname]))

        if os.path.isdir(PUB):
            for f in sorted(os.listdir(PUB)):
                if f not in files:
                    problems.append('ORPHAN: fy28/public/reference/%s is published and is '
                                    'in no index' % f)

        if problems:
            raise SystemExit('\n'.join(problems) + '\n  Run: python3 '
                             'scripts/build_reference_pages.py')
        print('ok: %d reference documents, %d published files, each byte for byte what '
              'this script produces from its source' % (len(data['pages']), len(files)))
        return 0

    os.makedirs(PUB, exist_ok=True)
    for fname, blob in sorted(files.items()):
        with open(os.path.join(PUB, fname), 'wb') as fh:
            fh.write(blob)

    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    with open(INDEX, 'w', encoding='utf-8') as fh:
        fh.write(fresh)

    print('wrote %d files to %s' % (len(files), os.path.relpath(PUB, ROOT)))
    for p in data['pages']:
        print('  %-28s %-9s %s%s' % (p['url'], p['door'],
                                     '' if p['generators'] else 'HAND-WRITTEN',
                                     '  raw: %s' % p['raw'] if p['raw'] else ''))
    print('wrote %s' % os.path.relpath(INDEX, ROOT))
    print('  %d excluded, each with its reason: %s'
          % (len(data['excluded']), ', '.join(os.path.basename(e['source'])
                                              for e in data['excluded'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
