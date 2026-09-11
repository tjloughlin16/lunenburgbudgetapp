#!/usr/bin/env python3
"""The candidates file, parsed. This is a LIBRARY, not a generator.

`notes/process/CONTENT-CANDIDATES.md` is the content. TJ edits it in Zed; that is the
editor, and there is no other one. This reads it and hands the items to
`scripts/build_blog.py`, which is the only thing that writes anything into the site.

WHY IT IS PARSED AND NOT RETYPED. Rule 2, and the consequence here is sharper than usual:
a post is the one artefact this project makes that CANNOT BE CORRECTED ONCE IT IS SHARED.
A figure typed into a component is wrong on a page somebody can reload; a figure typed
into a Facebook post is wrong on somebody else's timeline forever. So the copy has exactly
one home and everything follows it.

THE PARSE ASSERTS ITSELF. A parser that silently drops an item is the join-that-matched-
nothing failure this repo keeps hitting, and here it would drop content that has already
been reviewed. Fewer items than the floor, an item with no format, a format that is not
one of the four, a myth registry row pointing at an item or a conclusion that does not
exist -- each one refuses to go on.

WHAT THIS USED TO DO AND NO LONGER DOES. It used to write
`fy28/public/data/content-cards.json` -- all 48 items, every editorial field, the
character budgets, the over-by counts -- and /worth-knowing rendered it. Two things were
wrong with that. The copy of every UNDATED item was on the public site, which is exactly
what TJ said must not happen (*"the content shouldnt exist on the site anywhere"*); and
the editorial apparatus was a product, when it is a person reading a markdown file. Both
are gone. `check_content_cards.py` still prints the over-budget worklist at a terminal,
which is where a worklist belongs.

THREE DATES, AND THEY ARE NOT THE SAME DATE.

  1. `vintage` -- WHAT YEAR THE FIGURE IS ABOUT. Required, and it is an accuracy matter:
     $109,753 is right today and wrong in three years. Taken from the item's own copy
     where the copy states it, and otherwise from the SOURCE CONCLUSION's payload -- never
     inferred. Nine items yield none and are flagged `vintage: null` rather than given a
     plausible year.
  2. `source_updated` -- when the report behind the item last changed, out of
     `reports.json`. A fact about the archive rather than an editorial decision.
  3. `publish` -- THE ONE FIELD THAT DECIDES ANYTHING. `**Publish** — YYYY-MM-DD` in the
     item, and `None` when it is absent. Absent is not a state to be modelled; it is an
     absence, and it means the item does not leave this repository. Nothing here ever
     manufactures one.

THE EPISTEMIC LABEL SURVIVES THE TRIM. Every backticked conclusion id in an item's Source
line is resolved against the published payloads and its `kind` is read. One of the
archive's conclusions is a `hypothesis`, and a post built on it must never render as a
fact -- so a resolved hypothesis sets `epistemic: 'hypothesis'` and the page draws the
scenario rule. A run where NOTHING resolved refuses to go on.
"""

import csv
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

DOC = os.path.join(ROOT, 'notes', 'process', 'CONTENT-CANDIDATES.md')
MYTHS = os.path.join(ROOT, 'sources', 'data', 'myths.csv')
DATA = os.path.join(ROOT, 'fy28', 'public', 'data')
PAGES = os.path.join(ROOT, 'fy28', 'src', 'pages')
ROUTES = os.path.join(ROOT, 'fy28', 'src', 'routes.ts')

# The four formats the collaborator proposed and TJ adopted. A fifth is a decision about
# the programme, not a value to find in a document, so an unknown one refuses to write.
FORMATS = {
    'new finding': 'new-finding',
    'myth vs fact': 'myth-vs-fact',
    'did you know': 'did-you-know',
    'analysis spotlight': 'analysis-spotlight',
}
LABEL = {
    'new-finding': 'New finding',
    'myth-vs-fact': 'Myth vs fact',
    'did-you-know': 'Did you know?',
    'analysis-spotlight': 'Analysis spotlight',
}
# The one assumption on the page, and it is stated there rather than buried here: a
# reading time is words divided by a rate somebody chose. 200 wpm is the ordinary adult
# prose figure; these documents are tables and money, which is slower, so the estimate is
# generous and says so.
WORDS_PER_MINUTE = 200

# 48 items are in list 1 today. The floor is what stops a broken regex reporting success
# on three of them; it is deliberately the real count, so REMOVING an item is also a
# decision somebody has to make here rather than something that happens quietly.
MIN_ITEMS = 48

# A fiscal year, and NOT the tail of a decimal. `0.2048` gave item 5.3 a vintage of
# FY2048 -- the digits are there and the \b matched, because a word boundary sits happily
# after a decimal point. So: nothing may precede it that makes it part of a longer number.
YEAR = re.compile(r'(?<![\d.,])(?:FY|SY)?((?:19|20)\d{2})(?!\d)')


# ---- the archive this copy rests on -------------------------------------------------

def conclusion_index():
    """Every published conclusion, by id, with the payload file it came from."""
    idx = {}
    for f in sorted(os.listdir(DATA)):
        if not f.endswith('.json'):
            continue
        try:
            d = json.load(io.open(os.path.join(DATA, f), encoding='utf-8'))
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        for c in d.get('conclusions', []):
            if isinstance(c, dict) and c.get('id'):
                idx[c['id']] = (f, c)
    if not idx:
        raise SystemExit('no conclusions found in %s — refusing to write' % DATA)
    return idx


def payload_routes():
    """payload file -> the site address of the page that renders it.

    Read off the app rather than kept as a second list: a page declares `const TAB` and
    `const DATA`, and routes.ts says what URL a tab has. The join is asserted, because a
    regex that matches nothing here looks exactly like a set of reports with no pages.
    """
    src = io.open(ROUTES, encoding='utf-8').read()
    blk = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not blk:
        raise SystemExit('routes.ts: could not find the SLUG table')
    slug = dict(re.findall(r"^\s*(\w+): '([^']*)',", blk.group(1), re.M))
    if not slug:
        raise SystemExit('routes.ts: the SLUG table parsed to nothing')
    out = {}
    for f in sorted(os.listdir(PAGES)):
        if not f.endswith('.tsx'):
            continue
        text = io.open(os.path.join(PAGES, f), encoding='utf-8').read()
        t = re.search(r"^const TAB: Tab = '([a-z]+)'", text, re.M)
        d = (re.search(r"^const DATA = '/data/([^']+)'", text, re.M)
             or re.search(r"useReport<[^>]*>\('([^']+)'\)", text))
        if t and d and t.group(1) in slug:
            out.setdefault(d.group(1), '/' + slug[t.group(1)])
    if not out:
        raise SystemExit('no page component joined a payload to a route — refusing to '
                         'write, because every card would then link to /reports')
    return out


def git_date(relpath):
    """When the file behind a card last changed. A fact about the repository."""
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', relpath],
                             cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out or None
    except Exception:
        return None


def reports_by_url():
    """Every report the index knows, by its address — documents AND routed pages.

    A DOCUMENT carries `words` and `updated` and is the only thing a reading time can be
    computed for. A PAGE carries neither, so "when the source last changed" is taken from
    the git date of the PAYLOAD it renders — which is the thing that actually changes when
    a finding moves. Both are facts; neither is an editorial ordering.
    """
    p = os.path.join(DATA, 'reports.json')
    if not os.path.exists(p):
        raise SystemExit('missing fy28/public/data/reports.json — run '
                         'scripts/build_reports_index.py first')
    d = json.load(io.open(p, encoding='utf-8'))
    out = {r['url']: dict(r) for r in d.get('reports', []) if r.get('url')}
    for r in d.get('pages', []):
        if not r.get('url'):
            continue
        row = dict(r)
        du = (r.get('data') or {}).get('url')
        if du:
            row['updated'] = git_date('fy28/public' + du)
        out.setdefault(r['url'], row)
    if not out:
        raise SystemExit('reports.json named no reports and no pages — refusing to write')
    return out


# ---- the copy ------------------------------------------------------------------------

def ready_items(text):
    """The items in list 1, in file order. `### 1.1 Title`."""
    if '# 1. READY' not in text:
        raise SystemExit('CONTENT-CANDIDATES.md: no "# 1. READY" heading')
    ready = text.split('# 1. READY', 1)[1].split('\n# 2. NEEDS WORK FIRST', 1)[0]
    parts = re.split(r'^### (\d+\.\d+) (.+)$', ready, flags=re.M)
    for i in range(1, len(parts), 3):
        yield parts[i].strip(), parts[i + 1].strip(), parts[i + 2]


def field(body, name):
    """A labelled line out of the metadata block.

    Three shapes are in the file and all three are real: `**Source** — text`,
    `**FOR:** text`, and `**Strength — very high.** text`, where the em dash and the
    value are INSIDE the bold. Matching only the first shape is how `audience` and
    `strength` came back empty on every one of 48 items — a join that matched nothing,
    which is why this returns the whole labelled line rather than guessing a separator.
    """
    m = re.search(r'\*\*%s\s*(?:[—-]\s*(?P<inner>[^*]*))?\*\*\s*[—-]?\s*'
                  r'(?P<rest>.*?)(?=\n- \*\*|\n\n|\Z)' % re.escape(name), body, re.S)
    if not m:
        return ''
    val = ' '.join(x for x in ((m.group('inner') or '').strip(),
                               (m.group('rest') or '').strip()) if x)
    return re.sub(r'\s+', ' ', val).strip()


def sentences(s):
    """Split on sentence ends only. Never mid-sentence — that is the whole point."""
    out = [x.strip() for x in re.split(r'(?<=[.!?])\s+(?=[A-Z“"\*$£€\d])', s) if x.strip()]
    return out or ([s] if s.strip() else [])


def parse_item(n, title, body, idx):
    visible = body.split('<details>')[0]
    meta = body.split('<details>')[1] if '<details>' in body else ''

    head = re.search(r'^> ### (.+)$', visible, re.M)
    support = [l[2:].rstrip() for l in visible.split('\n')
               if l.startswith('> ') and not l.startswith('> ###')
               and not l.strip().lstrip('> ').startswith('*—')]
    contrast = re.search(r'^> \*— (.+?)\*\s*$', visible, re.M)
    impacts = re.findall(r'^\*\*If you are ([^:]+):\*\* (.+)$', visible, re.M)
    take = re.search(r'\*\*What we expect the reader to take away\*\*\s*(.*?)(?=\n\n|\Z)',
                     visible, re.S)
    # The format, and only the format. Items write it several ways -- "Myth vs Fact",
    # "Did You Know (mechanism: ...)", "Analysis Spotlight → `/health-insurance`." -- so
    # the letters are taken and then matched against the four by name rather than by
    # trusting a terminator to be there.
    fmt = re.search(r'\*\*Format\*\*\s*—\s*([A-Za-z ]+)', meta)

    if not head:
        raise SystemExit('item %s has no `> ### headline` — refusing to write' % n)
    if not fmt:
        raise SystemExit('item %s declares no **Format** — refusing to write' % n)
    key = re.sub(r'\s+', ' ', fmt.group(1)).strip().lower()
    key = next((k for k in FORMATS if key.startswith(k)), key)
    if key not in FORMATS:
        raise SystemExit('item %s has format %r, which is not one of the four: %s'
                         % (n, key, ', '.join(sorted(FORMATS))))

    # Every backticked token in the Source line that IS a published conclusion. The rest
    # are table names and page slugs and are counted, not guessed at.
    src = field(meta, 'Source')
    cited = [t for t in re.findall(r'`([a-z0-9][a-z0-9-]{4,})`', src) if t in idx]
    unresolved = [t for t in re.findall(r'`([a-z0-9][a-z0-9-]{4,})`', src) if t not in idx]
    # A slug may be written on the Source line OR on the Format line -- item 3.6 says
    # "Analysis Spotlight → `/health-insurance`" and nowhere else. Reading only one of the
    # two sent that card to /reports, which is the silent-wrong-answer shape: a link that
    # resolves and is not the page the item is about.
    slugs = re.findall(r'(?<![\w/])(/[a-z0-9][a-z0-9-]*)',
                       src + ' ' + field(meta, 'Format'))

    return dict(
        n=n, title=title.strip(),
        format=FORMATS[key],
        headline=re.sub(r'\s+', ' ', head.group(1)).strip(),
        support=re.sub(r'\s+', ' ', ' '.join(x for x in support if x.strip())).strip(),
        contrast=contrast.group(1).strip() if contrast else '',
        impacts=[dict(who=w.strip(), text=re.sub(r'\s+', ' ', t).strip())
                 for w, t in impacts],
        takeaway=re.sub(r'\s+', ' ', take.group(1)).strip() if take else '',
        format_note=field(meta, 'Format'),
        source_text=src,
        strength=field(meta, 'Strength'),
        audience=field(meta, 'FOR:'),
        also=field(meta, 'ALSO REACHES:'),
        why_reader=field(meta, 'Why this reader'),
        must_carry=[re.sub(r'\s+', ' ', m).strip() for m in
                    re.findall(r'\*\*Must carry\*\*\s*—\s*(.+?)(?=\n- \*\*|\n\n|\Z)',
                               meta, re.S)],
        cited=cited, unresolved=unresolved, slugs=slugs,
        publish=(re.search(r'\*\*Publish\*\*\s*—\s*(\d{4}-\d{2}-\d{2})', body).group(1)
                 if re.search(r'\*\*Publish\*\*\s*—\s*(\d{4}-\d{2}-\d{2})', body)
                 else None),
        _visible=visible,
    )


def vintage_of(it, idx):
    """What year the card's figure is ABOUT. From the copy, else from the payload."""
    ys = [int(y) for y in YEAR.findall(it['_visible'])]
    where = 'card'
    if not ys:
        # The conclusion's PROSE and the rendered text of its figures -- not the raw
        # JSON, whose numeric `value` fields are decimals that look like years.
        pool = []
        for cid in it['cited']:
            c = idx[cid][1]
            pool.append(c.get('detail', ''))
            pool.append(c.get('basis', ''))
            for f in (c.get('figures') or {}).values():
                if isinstance(f, dict):
                    pool.append(str(f.get('text', '')))
                    pool.append(str(f.get('unit', '')))
        ys = [int(y) for y in YEAR.findall(' '.join(pool))]
        where = 'payload'
    if not ys:
        return None, None, None
    return min(ys), max(ys), where


def items():
    """Every ready item, parsed, in file order.

    The list is deliberately ALL of them. The gate -- which of these may leave the
    repository -- is one test in `build_blog.py`, applied at the point of WRITING, because
    a filter applied at the point of rendering leaves the copy sitting in a published file
    for anybody who fetches it directly.
    """
    text = io.open(DOC, encoding='utf-8').read()
    idx = conclusion_index()

    myths = {}
    with io.open(MYTHS, encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            myths[row['item'].strip()] = row

    out, resolved_total = [], 0
    for n, title, body in ready_items(text):
        it = parse_item(n, title, body, idx)
        resolved_total += len(it['cited'])
        v_lo, v_hi, v_from = vintage_of(it, idx)

        myth = myths.get(n)
        if myth:
            if myth['conclusion_id'] not in idx:
                raise SystemExit(
                    'myths.csv row %s names conclusion %r, which no published payload '
                    'carries' % (n, myth['conclusion_id']))
            if idx[myth['conclusion_id']][1].get('kind') != 'measured':
                raise SystemExit(
                    'myths.csv row %s rests on conclusion %r, which is a %s and may not '
                    'be rendered as a fact'
                    % (n, myth['conclusion_id'], idx[myth['conclusion_id']][1]['kind']))

        kinds = {idx[c][1].get('kind') for c in it['cited']}
        it.update(
            id='item-' + n.replace('.', '-'),
            label=LABEL[it['format']],
            vintage=v_hi, vintage_from=v_from,
            vintage_span=([v_lo, v_hi] if v_hi is not None and v_lo != v_hi else None),
            epistemic=('hypothesis' if 'hypothesis' in kinds else 'measured'),
            bearings=sorted({idx[c][1].get('bearing') for c in it['cited']
                             if idx[c][1].get('bearing')}),
            myth=(dict(myth=myth['myth'], mechanism=myth['mechanism'],
                       conclusion=myth['conclusion_id'], note=myth['note'])
                  if myth else None),
        )
        out.append(it)

    if len(out) < MIN_ITEMS:
        raise SystemExit(
            'parsed %d ready items and the floor is %d. A parser that drops an item looks '
            'exactly like a shorter list.' % (len(out), MIN_ITEMS))
    if not resolved_total:
        raise SystemExit(
            'not one backticked conclusion id in the candidates file resolved against a '
            'published payload. A join that matches nothing looks exactly like data that '
            'is absent.')
    for row in myths:
        if row not in {c['n'] for c in out}:
            raise SystemExit('myths.csv names item %s, which is not in list 1' % row)
    return out
