#!/usr/bin/env python3
"""BLOCKS: the parts of a topic page or hub that the author ARRANGES, rather than fills in.

TJ, 25 October 2026, after a page explaining which family moves make a special education
surprise cost was built outside the framework and read better than anything inside it:
*"when we build topic pages and such, i need you to be able to have the flexibility you just
did to build this page. please open up our ruleset to allow that. i didnt mean to constrain
outcomes. you clearly have been constrained."*

He was right, and the constraint was specific. Every chart type in topic.py draws a QUANTITY
(series, ranking, parts, bridge, presence), every conclusion is a metric and two lines, and
the words a page may use are counted as if every one of them were read top to bottom. A page
whose answer is a MECHANISM -- who pays, under which rule, from when -- had nowhere to go. The
answer got cut to fit the slots, or was never attempted.

SO THE RULES SPLIT IN TWO, and only one half is relaxed here:

    INTEGRITY -- unchanged, and every block below is held to it:
        rule 2   every digit is a registered figure or a declared literal (brief.check_unit)
        rule 3   every claim in a cell says what it rests on: `basis`, one of BASIS_KINDS
        rule 7   our reading is drawn as our reading, never as the law or the record
        rule 8   nothing tells the reader what to do (PRESCRIPTIVE)
        and      no figures without an insight: a block that shows numbers -- panels, chart,
                 custom -- carries `so`, WHAT IT MEANS, the same line a ladder conclusion
                 carries. TJ, 25 October 2026: "follow the 'what it means' pattern so we dont
                 put important metrics without an insight to understand them."

    SHAPE -- now the author's call:
        which blocks, in what order (`place`), how many, and how much they say. Block words do
        NOT count toward the page's TOPIC_WORDS_MAX: words inside a diagram are found by
        position, not read top to bottom. The site-wide reading-time ratchet
        (build_reading_time.py) still measures the whole page.

The per-unit caps below are runaway guards, not a format: generous enough that nothing a
reader would want is cut, tight enough that a paragraph cannot silently become an essay.

    explain()  a box of plain paragraphs: a definition that leads, or "what this means"
    matrix()   a DECISION MATRIX: two dimensions a reader looks their case up by, and in each
               cell a verdict, what it lands on, why, and what that rests on
    timeline() a STATE TIMELINE: one row per case, periods across, each cell a state from a
               declared legend; an event marker and one reference line
    checks()   rows of causes against columns of things, a mark where one lands on the other
    panels()   two to four side-by-side cards of label/value rows, for a direct comparison
    custom()   ANYTHING ELSE. TJ, same day: *"you can build diagrams, charts, or whatever on
               the fly even if we dont have templates for them or havent used them before ...
               for ANY page, hub we build."* A page that needs a picture none of the above
               draws gets its own component -- fy28/src/components/blocks/custom/<id>.tsx,
               registered in that folder's index.ts -- fed by `data` from the generator.
               No template, no prior use, no permission needed. The only conditions are the
               integrity half: every digit in `data` is a figure the generator formatted
               (`figures`) or a declared literal, every claim names its basis, and it is a
               component drawn from the payload, never an image (rule 7f).

The five named blocks are not the menu. They are custom blocks that turned out to be useful
twice. When a custom block is reused on a second page, promote it to a builder here.

Every builder returns a plain dict with `block` (its type) and `place`:
    'top'   under the title and any lead quote (the claim tested comes first), above the
            finding: the page's
            headline conclusion (TJ, of the highest-impact callout: "put it at the top of the page")
    'lead'  after the finding (or a hub's answer), before the signature chart
    'chart' directly under the signature chart
    'also1' directly under the first `also` chart; 'also2' under the second -- so a block
            that explains a chart sits beside it, not three charts later
    'body'  after the charts and how-it-works, before the facts and conclusions (default)
    'end'   after the tables, before what was said
"""
from brief import _unit, check_unit, PRESCRIPTIVE
from conclusions import ConclusionError

PLACES = ('top', 'lead', 'chart', 'also1', 'also2', 'body', 'end')
# What a claim in a block rests on. The renderer draws `reading` in the estimate colour, so a
# reader can always tell our interpretation from a document's own words (rules 3 and 7).
BASIS_KINDS = ('law', 'record', 'budget', 'reading')
# Semantic tones a legend may use. They map to the site's status colours, never to the
# categorical series palette, so a verdict colour never reads as a data series.
TONES = ('bad', 'good', 'neutral', 'muted', 'other')

TITLE_MAX = 90
TEXT_MAX = 700          # one paragraph
CELL_MAX = 260          # a cell's "why"
LABEL_MAX = 90
ROWS_MAX = 40
COLS_MAX = 8
PERIODS_MAX = 24


def _u(x, cap, name):
    """str, or (str, figures), or (str, figures, allow) -> a checked unit."""
    t = x if isinstance(x, tuple) else (x,)
    u = _unit(t[0], t[1] if len(t) > 1 else None, t[2] if len(t) > 2 else (), cap, name)
    bad = check_unit(u, name)
    if PRESCRIPTIVE.search(u['text']):
        bad.append('%s tells the reader what to do: %r' % (name, u['text']))
    if bad:
        raise ConclusionError('\n  '.join(bad))
    return u


def _label(s, name, cap=LABEL_MAX):
    """A short label. Held to rule 2 like prose: a label with a digit must declare it."""
    return _u(s, cap, name)['text']


def _basis(b, name):
    """(kind, label): ('law', 'Statute: c.71B §5'), ('reading', 'Our reading')."""
    if not (isinstance(b, tuple) and len(b) == 2 and b[0] in BASIS_KINDS):
        raise ConclusionError('%s: basis must be (kind, label) with kind one of %s, got %r'
                              % (name, BASIS_KINDS, b))
    return dict(kind=b[0], label=_u((b[1], None, _digits(b[1])), LABEL_MAX, name + ' basis')['text'])


def _digits(s):
    """A basis label cites a document by number (c.71B §5, 603 CMR 28.10): those digits are
    an address, not a figure, so they are declared literals."""
    import re
    return tuple(re.findall(r'\d[\d,.]*', s))


def _place(p, name):
    if p not in PLACES:
        raise ConclusionError('%s: place %r is not one of %s' % (name, p, PLACES))
    return p


def _legend(items, name):
    out = []
    for it in items:
        key, label, tone = it[0], it[1], it[2]
        if tone not in TONES:
            raise ConclusionError('%s legend %r: tone %r is not one of %s' % (name, key, tone, TONES))
        out.append(dict(key=key, label=_label(label, name + ' legend'), tone=tone,
                        **({'pattern': it[3]} if len(it) > 3 else {})))
    if len({x['key'] for x in out}) != len(out):
        raise ConclusionError('%s: two legend entries share a key' % name)
    return out


def explain(title, paragraphs, place='lead', tone='define', figures_note=None):
    """Plain paragraphs under a title. `tone`: 'define' (a tinted box: what a thing IS, for a
    page whose words a reader may misread), 'plain' (no box: what the figures above mean), or
    'callout' (a ruled box: the one answer a reader came to find -- TJ, on the highest-impact
    setting: "i want to look for that").
    Each paragraph is a str or (str, figures, allow); **double asterisks** mark bold."""
    name = 'explain %r' % title
    if tone not in ('define', 'plain', 'callout'):
        raise ConclusionError('%s: tone %r' % (name, tone))
    ps = [_u(p, TEXT_MAX, '%s paragraph %d' % (name, i + 1)) for i, p in enumerate(paragraphs)]
    if not ps:
        raise ConclusionError('%s: no paragraphs' % name)
    return dict(block='explain', place=_place(place, name), title=_label(title, name, TITLE_MAX),
                tone=tone, paragraphs=ps)


SOLIDITY = ('published', 'estimate', 'gap')


def measure(label, value, solidity):
    """A figure on a matrix heading or cell, and HOW SOLID it is: 'published' (a record
    printed it), 'estimate' (ours), or 'gap' (nobody publishes it; `value` says what is
    unknown in words, e.g. "Unknown kids", and the renderer's red tag says "Gap in data" --
    never both, which reads as a stutter: TJ, "we have 2 'gap in data' labels"). TJ, 25 October 2026: "how many kids per year land in
    each category... and the cost, and how solid we know of the costs. that way, the school
    committee can fill in the gaps when people ask about it." `value` is formatted by the
    generator from the data, like a table cell; `label` is prose and held to rule 2."""
    return dict(label=label, value=value, solidity=solidity)


def _bad_chip(where, c):
    raise ConclusionError('%s: chip %r solidity is not one of %s' % (where, c, SOLIDITY))


def _measures(ms, name):
    out = []
    for m in ms or ():
        if m['solidity'] not in SOLIDITY:
            raise ConclusionError('%s: solidity %r is not one of %s' % (name, m['solidity'], SOLIDITY))
        out.append(dict(label=_label(m['label'], name + ' measure'), value=str(m['value']),
                        solidity=m['solidity']))
    return out


def cell(verdict, title, why, basis, lands_on=None, measures=(), chips=()):
    """One cell of a matrix(). `why` is str or (str, figures, allow). `chips`: [(label,
    solidity)] -- a short flag at the top of the cell, "Costliest per child", with how solid
    the comparison behind it is. TJ: "can you put those labels or chips on the cells if we
    know which box is costliest". The generator decides which cell wins, from the data."""
    return dict(verdict=verdict, title=title, why=why, basis=basis, lands_on=lands_on,
                measures=measures, chips=chips)


def matrix(title, rows, columns, cells, legend, place='lead', note=None,
           row_label='', col_label='', row_measures=(), col_measures=(), gaps=()):
    """A DECISION MATRIX. `rows` and `columns` are labels; `cells` maps (row index, column
    index) to cell(); every position must be filled -- a blank in a decision matrix is a case
    nobody answered, and that is a finding to state, not a gap to leave. `legend` is
    [(key, label, tone)]; every cell's verdict must be a legend key."""
    name = 'matrix %r' % title
    if not 2 <= len(columns) <= COLS_MAX or not 1 <= len(rows) <= ROWS_MAX:
        raise ConclusionError('%s: %d rows x %d columns' % (name, len(rows), len(columns)))
    lg = _legend(legend, name)
    keys = {x['key'] for x in lg}
    out = []
    for r in range(len(rows)):
        line = []
        for c in range(len(columns)):
            if (r, c) not in cells:
                raise ConclusionError('%s: no cell at row %r, column %r' % (name, rows[r], columns[c]))
            x = cells[(r, c)]
            w = '%s cell (%s, %s)' % (name, rows[r], columns[c])
            if x['verdict'] not in keys:
                raise ConclusionError('%s: verdict %r is not in the legend' % (w, x['verdict']))
            line.append(dict(verdict=x['verdict'], title=_label(x['title'], w + ' title'),
                             why=_u(x['why'], CELL_MAX, w + ' why'), basis=_basis(x['basis'], w),
                             measures=_measures(x.get('measures'), w),
                             chips=[dict(label=_label(c[0], w + ' chip', 40), solidity=c[1])
                                    for c in x.get('chips', ())
                                    if c[1] in SOLIDITY or _bad_chip(w, c)],
                             **({'lands_on': _label(x['lands_on'], w + ' lands on')}
                                if x.get('lands_on') else {})))
        out.append(line)
    extra = dict(note=_u(note, TEXT_MAX, name + ' note')) if note else {}
    if row_measures:
        if len(row_measures) != len(rows):
            raise ConclusionError('%s: one list of measures per row' % name)
        extra['row_measures'] = [_measures(m, '%s row %d' % (name, i + 1)) for i, m in enumerate(row_measures)]
    if col_measures:
        if len(col_measures) != len(columns):
            raise ConclusionError('%s: one list of measures per column' % name)
        extra['col_measures'] = [_measures(m, '%s column %d' % (name, i + 1)) for i, m in enumerate(col_measures)]
    if gaps:   # the questions a reader could put to whoever holds the answer (rule 7c)
        extra['gaps'] = [_u(g, CELL_MAX, '%s gap %d' % (name, i + 1)) for i, g in enumerate(gaps)]
    return dict(extra, block='matrix', place=_place(place, name), title=_label(title, name, TITLE_MAX),
                rows=[_label(r, name + ' row') for r in rows],
                columns=[_label(c, name + ' column') for c in columns],
                row_label=row_label, col_label=col_label, legend=lg, cells=out)


def track(label, states, note=None, event=None, cut=False, tags=(), verdict=None, basis=None):
    """One row of a timeline(). `states`: one legend key (or None: nothing) per period."""
    return dict(label=label, states=states, note=note, event=event, cut=cut, tags=tags,
                verdict=verdict, basis=basis)


def timeline(title, periods, groups, legend, place='body', marker=None, note=None,
             event_label='the event', verdicts=()):
    """A STATE TIMELINE. `periods`: short labels across (months, then 'Next yr'). `groups`:
    [(heading, [track()])]. `marker`: (index, label) -- a dashed line AFTER that period
    (when next year's budget is set). `event` on a track marks the period something happened."""
    name = 'timeline %r' % title
    if not 2 <= len(periods) <= PERIODS_MAX:
        raise ConclusionError('%s: %d periods' % (name, len(periods)))
    lg = _legend(legend, name)
    keys = {x['key'] for x in lg}
    vs = _legend(verdicts, name + ' verdicts') if verdicts else []
    gs = []
    for heading, tracks in groups:
        ts = []
        for t in tracks:
            w = '%s row %r' % (name, t['label'])
            if len(t['states']) != len(periods):
                raise ConclusionError('%s: %d states for %d periods' % (w, len(t['states']), len(periods)))
            if any(s is not None and s not in keys for s in t['states']):
                raise ConclusionError('%s: a state not in the legend' % w)
            if t['verdict'] and t['verdict'] not in {v['key'] for v in vs}:
                raise ConclusionError('%s: verdict %r is not in verdicts' % (w, t['verdict']))
            if t['event'] is not None and not 0 <= t['event'] < len(periods):
                raise ConclusionError('%s: event outside the periods' % w)
            ts.append(dict(label=_label(t['label'], w), states=list(t['states']),
                           event=t['event'], cut=bool(t['cut']),
                           tags=[_label(x, w + ' tag') for x in t['tags']],
                           **({'note': _u(t['note'], CELL_MAX, w + ' note')} if t['note'] else {}),
                           **({'verdict': t['verdict']} if t['verdict'] else {}),
                           **({'basis': _basis(t['basis'], w)} if t['basis'] else {})))
        if not ts:
            raise ConclusionError('%s: group %r is empty' % (name, heading))
        gs.append(dict(heading=_label(heading, name + ' group', TITLE_MAX), tracks=ts))
    if marker and not 0 <= marker[0] < len(periods) - 1:
        raise ConclusionError('%s: marker outside the periods' % name)
    extra = dict(note=_u(note, TEXT_MAX, name + ' note')) if note else {}
    if marker:
        extra['marker'] = dict(after=marker[0], label=_label(marker[1], name + ' marker'))
    return dict(extra, block='timeline', place=_place(place, name),
                title=_label(title, name, TITLE_MAX), periods=list(periods), legend=lg,
                verdicts=vs, groups=gs,
                event_label=_label(event_label, name + ' event'))


def check_row(label, why, marks, contrast=False):
    """One row of checks(): `marks` is the set of column indices it lands on. `contrast`
    draws the row as the exception -- the case that is NOT one of the others."""
    return dict(label=label, why=why, marks=marks, contrast=contrast)


def checks(title, columns, rows, place='body', note=None, first='What happens',
           second='Why', tone='bad', so=None):
    """Rows of things against columns, a mark where one lands on the other, with a reason per
    row. The causes of a surprise cost against the budget lines they reach. `tone`: the mark's
    colour -- 'bad' (it lands there: a cost) or 'good' (it holds: a reserve that covered a year)."""
    if tone not in ('bad', 'good'):
        raise ConclusionError('checks %r: tone %r' % (title, tone))
    name = 'checks %r' % title
    if not 1 <= len(columns) <= COLS_MAX or not 1 <= len(rows) <= ROWS_MAX:
        raise ConclusionError('%s: %d rows x %d columns' % (name, len(rows), len(columns)))
    rs = []
    for r in rows:
        w = '%s row %r' % (name, r['label'])
        if any(not 0 <= m < len(columns) for m in r['marks']):
            raise ConclusionError('%s: a mark outside the columns' % w)
        rs.append(dict(label=_label(r['label'], w, TITLE_MAX), why=_u(r['why'], CELL_MAX, w + ' why'),
                       marks=sorted(r['marks']), contrast=bool(r['contrast'])))
    extra = dict(note=_u(note, TEXT_MAX, name + ' note')) if note else {}
    if so:
        extra['so'] = _so(so, name)
    return dict(extra, block='checks', tone=tone, place=_place(place, name), title=_label(title, name, TITLE_MAX),
                columns=[_label(c, name + ' column') for c in columns], rows=rs,
                first=first, second=second)


def _so(so, name):
    """WHAT IT MEANS: one line, our reading of the figures for the decision -- str or
    (str, figures, allow), held to rule 2 and rule 8 like every other unit. Required on a
    block that shows numbers (see the module header)."""
    if not so:
        raise ConclusionError('%s shows figures and says nothing about what they mean: pass so='
                              % name)
    return _u(so, CELL_MAX, name + ' what it means')


def panel(title, rows, sub=None, so=None):
    """One card of panels(). `rows`: [(label, value_text, tone or None)]; value_text is
    formatted by the generator (C.usd and friends) from the data, like a table cell.
    `so`: what this card's figures mean, when each card answers its own question."""
    return dict(title=title, rows=rows, sub=sub, so=so)


def panels(title, cards, place='body', note=None, so=None):
    """Two to four cards side by side, for a comparison read across: private against
    collaborative. Each value is a figure the generator formatted; tone colours it.
    `so` on the block, or on every card: what the figures mean."""
    name = 'panels %r' % title
    if not so and not all(c.get('so') for c in cards):
        raise ConclusionError('%s shows figures and says nothing about what they mean: pass so= '
                              'on the block or on every card' % name)
    if not 2 <= len(cards) <= 4:
        raise ConclusionError('%s: %d cards; two to four' % (name, len(cards)))
    cs = []
    for c in cards:
        w = '%s card %r' % (name, c['title'])
        rows = []
        for r in c['rows']:
            if r[2] is not None and r[2] not in TONES:
                raise ConclusionError('%s: tone %r' % (w, r[2]))
            rows.append(dict(label=_label(r[0], w + ' label'), value=str(r[1]), tone=r[2]))
        cs.append(dict(title=_label(c['title'], w), rows=rows,
                       **({'sub': _u(c['sub'], CELL_MAX, w + ' sub')} if c.get('sub') else {}),
                       **({'so': _so(c['so'], w)} if c.get('so') else {})))
    extra = dict(note=_u(note, TEXT_MAX, name + ' note')) if note else {}
    if so:
        extra['so'] = _so(so, name)
    return dict(extra, block='panels', place=_place(place, name), title=_label(title, name, TITLE_MAX),
                cards=cs)


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _strings(v)


def custom(component, title, data, place='body', figures=(), allow=(), basis=None, alt=None,
           so=None):
    """A one-off diagram, drawn by fy28/src/components/blocks/custom/<component>.tsx from
    `data` (any JSON). Rule 2 still holds over every string in `data`: a digit must be part of
    a display string in `figures` (formatted by the generator from the data: C.usd, C.pct) or
    a declared literal in `allow` (a statute number, a month). Numbers as numbers -- values a
    component scales a mark by -- are not prose and are not checked. `basis`: (kind, label)
    when the whole diagram rests on one thing; otherwise put a basis in each claim's data."""
    import re
    name = 'custom %r' % component
    if not re.fullmatch(r'[a-z][a-z0-9-]*', component):
        raise ConclusionError('%s: a component id is lowercase words and hyphens' % name)
    ok = sorted(set(figures) | set(allow), key=len, reverse=True)
    bad = []
    for s in _strings(data):
        r = s
        for t in ok:
            r = r.replace(t, ' ')
        left = re.findall(r'\d[\d,.]*', r)
        if left:
            bad.append('%s: %r carries %s, not a registered figure or declared literal'
                       % (name, s[:80], ', '.join(left)))
        if PRESCRIPTIVE.search(s):
            bad.append('%s: %r tells the reader what to do' % (name, s[:80]))
    if bad:
        raise ConclusionError('\n  '.join(bad))
    extra = dict(basis=_basis(basis, name)) if basis else {}
    extra['so'] = _so(so, name)
    return dict(extra, block='custom', place=_place(place, name), component=component,
                title=_label(title, name, TITLE_MAX), data=data,
                alt=alt or title)


def chart(spec, place='body', so=None):
    """Any chart topic.py builds (series, ranking, parts, bridge, presence, image), placed where
    it explains something instead of in the page's fixed chart slots. A hub that answers three
    questions can draw a chart for each."""
    import topic as _TP   # topic imports this module; import here to keep that one-way
    bad = _TP.check_chart(spec, 'chart block %r' % (spec or {}).get('title'), required=True)
    if bad:
        raise ConclusionError('\n  '.join(bad))
    return dict(block='chart', place=_place(place, 'chart block'), spec=spec,
                so=_so(so, 'chart block %r' % spec.get('title')))


def terms(title, items, place='end'):
    """Definitions: what each thing IS and why it surprises, built by topic.term(). TJ, 25
    October 2026: definitions belong on a deeper page "to learn more", the hub keeps the big
    conclusions -- so terms became a block any topic page can carry."""
    for t in items:
        if set(t) != {'term', 'means', 'surprises'}:
            raise ConclusionError('terms %r: an item not built by topic.term()' % title)
    return dict(block='terms', place=_place(place, 'terms %r' % title),
                title=_label(title, 'terms', TITLE_MAX), items=list(items))


KINDS = ('explain', 'matrix', 'timeline', 'checks', 'panels', 'custom', 'chart', 'terms')


def blocks_bad(blocks, where):
    """A payload's blocks were built by the builders above. The builders refuse on their own;
    this catches a dict typed by hand, which would skip every check."""
    bad = []
    for i, b in enumerate(blocks):
        if not isinstance(b, dict) or b.get('block') not in KINDS or b.get('place') not in PLACES:
            bad.append('%s block %d: not built by topic_blocks (%r)' % (where, i + 1,
                       b.get('block') if isinstance(b, dict) else b))
        elif b['block'] in ('chart', 'custom') and not b.get('so') or b['block'] == 'panels' and \
                not b.get('so') and not all(c.get('so') for c in b['cards']):
            bad.append('%s block %d (%s): figures with no "what it means"' % (where, i + 1, b['block']))
    return bad
