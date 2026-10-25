#!/usr/bin/env python3
"""The fact ladder: the top of a report built bottom-up, from bare facts to conclusions.

A TEMPLATE FOR MANY REPORTS, prototyped on /analysis/transportation. TJ, 12 October 2026:
*"simple facts. NOT long sentences or paragraphs of the basic facts. Then build on those
facts. what are the second tier facts people need to understand. then third tier until we
get to conclusions."* And: *"how do we show these metrics in a way that is clear, not a huge
scroll, and easy to understand?"*

The shape is the LADDER OF ABSTRACTION. Each rung generalises the one below it, and a reader
can climb down from any conclusion to the facts it rests on:

    tier 1   the facts         what it costs, what one unit of it costs, how much of it there is
    tier 2   how it changes    rates, comparisons against a limit, what is already fixed
    tier 3   who pays / what the budget shows
    conclusions               short sentences, each naming the facts it rests on (`rests_on`)

THE UNIT IS A FACT, NOT A SENTENCE. A fact is a VALUE (one registered figure, rendered) and a
LABEL that carries the unit and the year -- rule 7b's "a bare number in a stat box abandons
the discipline at the moment a reader is most likely to quote it". No prose under a fact.
Anything longer belongs a layer down in the page.

EVERY FACT SAYS WHAT KIND IT IS (rule 3), because a tile does not have room for a sentence
saying so:

    published   printed by the books, a budget or another publisher
    contract    fixed by a signed contract or its bid form
    statute     fixed by law
    estimate    OURS -- drawn in the estimate colour and marked on the tile
    gap         not published; the value is a dash, and `closes` names what would settle it

WHY THE BUDGETS ARE WHAT THEY ARE. Tiles sit two to a row on a 368px phone column, so each
is about 170px wide. The value is 20px tabular, about 11px a figure: 14 characters fit. The
label is 12.5px, about 6.6px a character, so about 25 a line; 60 is two and a half lines,
which is as much as a tile can hold before the grid turns ragged. A conclusion is 15px in
the full 368px: 110 is three lines on a phone, one breath.

The rule-2 check is brief.check_unit, unchanged: every registered figure appears in the text
and no digit is left that is neither a figure nor a declared literal. Run on the value, the
label and every conclusion. And a conclusion that rests on a fact which is not on the page
is refused -- that is the whole promise of the ladder.
"""
import re

from brief import _unit, check_unit, PRESCRIPTIVE
from conclusions import ConclusionError, figure  # noqa: F401  (figure is re-exported)

KINDS = ('published', 'contract', 'statute', 'estimate', 'gap')

VALUE_MAX = 14
LABEL_MAX = 60
TITLE_MAX = 40
CONCLUSION_MAX = 110
CLOSES_MAX = 150
FACTS = (2, 14)          # fewer than two is not a tier; more than fourteen is a table
TIERS = (2, 3)
CONCLUSIONS = (2, 6)      # six one-line conclusions is one phone screen

ID_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def fact(id, value, label, kind, label_figures=None, allow=(), closes=None):
    """One tile. `value` is built by figure(); for a `gap` it is None and renders as a dash.
    `label_figures` and `allow` cover any figure or literal the LABEL states (a year, a base)."""
    if not ID_RE.match(id or ''):
        raise ConclusionError('fact id %r is not a slug' % (id,))
    if kind not in KINDS:
        raise ConclusionError('%s: kind %r is not one of %s' % (id, kind, KINDS))
    if kind == 'gap':
        if value is not None:
            raise ConclusionError('%s: a gap has no value; it is the dash' % id)
        if not closes:
            raise ConclusionError('%s: a gap must say what would settle it' % id)
    else:
        if not (isinstance(value, dict) and set(value) == {'value', 'text', 'unit'}):
            raise ConclusionError('%s: the value was not built by figure()' % id)
        if len(value['text']) > VALUE_MAX:
            raise ConclusionError('%s: value %r is %d characters, budget %d'
                                  % (id, value['text'], len(value['text']), VALUE_MAX))
    lab = _unit(label, label_figures, allow, LABEL_MAX, '%s label' % id)
    out = dict(id=id, kind=kind, value=value, label=lab)
    if closes:
        c = ' '.join(closes.split())
        if len(c) > CLOSES_MAX:
            raise ConclusionError('%s: closes is %d characters, budget %d' % (id, len(c), CLOSES_MAX))
        out['closes'] = c
    return out


def tier(title, facts):
    t = ' '.join(title.split())
    if not t or len(t) > TITLE_MAX:
        raise ConclusionError('tier title %r is over %d characters' % (t, TITLE_MAX))
    if not FACTS[0] <= len(facts) <= FACTS[1]:
        raise ConclusionError('tier %r has %d facts; a tier holds %d to %d'
                              % ((t, len(facts)) + FACTS))
    return dict(title=t, facts=list(facts))


SO_MAX = 140


def conclusion(text, rests_on, figures=None, allow=(), chain=None, so=None, so_figures=None,
               so_allow=()):
    """One rung at the top. `rests_on` names the facts under it; `chain` optionally names a
    question in the brief whose verdict and evidence open beneath it. TJ, 12 October 2026:
    the conclusions and the questions "seem to be the same type of information" -- so a
    question is no longer a second list, it is the evidence for a conclusion.

    `so`: WHAT IT MEANS -- the line under the fact saying what it changes for a decision or a
    reader. TJ, 24 October 2026: "we give a fact, which is AMAZING. but what does the fact mean
    or suggest? ... how does it impact decision making or citizens or boards". It is our
    reading of the fact, so it is drawn as such; it may not instruct (PRESCRIPTIVE), and every
    figure in it is registered like any other."""
    u = _unit(text, figures, allow, CONCLUSION_MAX, 'conclusion')
    if not rests_on:
        raise ConclusionError('a conclusion must rest on at least one fact: %r' % text)
    u['rests_on'] = list(rests_on)
    if chain:
        u['chain'] = chain
    if so:
        m = _unit(so, so_figures, so_allow, SO_MAX, 'conclusion means')
        bad = check_unit(m, 'conclusion means')
        if PRESCRIPTIVE.search(m['text']):
            bad.append('what it means tells the reader what to do: %r' % m['text'])
        if bad:
            raise ConclusionError('\n  '.join(bad))
        u['so'] = m
    return u


def matrix(columns, rows, place):
    """An optional second arrangement of the SAME facts: a column per thing the report
    compares (kinds of bus, schools, funds) and a row per rung. Read across a row to
    compare; read down a column for one thing's whole story. `columns` and `rows` are
    (id, label) pairs, a column may add a tone (a CSS colour token, matched to the page's
    charts); `place` maps (column id, row id) to the fact ids in that cell, in order. An
    empty cell is drawn empty: in a matrix the blank is part of the finding."""
    cols = [dict(id=c[0], label=c[1], tone=c[2] if len(c) > 2 else None) for c in columns]
    rws = [dict(id=r[0], label=r[1]) for r in rows]
    cells = [dict(col=c, row=r, facts=list(ids)) for (c, r), ids in place.items()]
    return dict(columns=cols, rows=rws, cells=cells)


def ladder(tiers, conclusions, title='What it adds up to', matrix=None, chains=()):
    """Validate the whole ladder and return it ready for a payload. Refuses rather than warns."""
    if not TIERS[0] <= len(tiers) <= TIERS[1]:
        raise ConclusionError('%d tiers; a ladder has %d to %d' % ((len(tiers),) + TIERS))
    if not CONCLUSIONS[0] <= len(conclusions) <= CONCLUSIONS[1]:
        raise ConclusionError('%d conclusions; a ladder has %d to %d'
                              % ((len(conclusions),) + CONCLUSIONS))
    ids = [f['id'] for t in tiers for f in t['facts']]
    if len(set(ids)) != len(ids):
        raise ConclusionError('two facts share an id')
    out = dict(tiers=list(tiers), conclusions=list(conclusions), title=title)
    if matrix:
        out['matrix'] = matrix
    bad = check(out)
    # Every chain a conclusion names must exist, and no chain may sit under two conclusions:
    # the evidence for a claim is said once.
    named = [c['chain'] for c in conclusions if c.get('chain')]
    for n in named:
        if n not in chains:
            bad.append('a conclusion names chain %r, which the brief does not carry' % n)
    if len(set(named)) != len(named):
        bad.append('two conclusions name the same chain')
    if bad:
        raise ConclusionError('the ladder did not pass:\n  ' + '\n  '.join(bad))
    return out


def check(l):
    """Every problem with a ladder, as strings. Empty means it passes."""
    bad = []
    ids = {f['id'] for t in l['tiers'] for f in t['facts']}
    for t in l['tiers']:
        for f in t['facts']:
            bad += check_unit(f['label'], '%s label' % f['id'])
            for where, text in (('label', f['label']['text']), ('closes', f.get('closes', ''))):
                if PRESCRIPTIVE.search(text):
                    bad.append('%s %s tells the reader what to do: %r' % (f['id'], where, text))
    m = l.get('matrix')
    if m:
        cids, rids = {c['id'] for c in m['columns']}, {r['id'] for r in m['rows']}
        seen = []
        for cell in m['cells']:
            if cell['col'] not in cids or cell['row'] not in rids:
                bad.append('matrix cell %s/%s names a column or row that is not declared'
                           % (cell['col'], cell['row']))
            for f in cell['facts']:
                if f not in ids:
                    bad.append('matrix cell %s/%s places %r, which is not a fact'
                               % (cell['col'], cell['row'], f))
            seen += cell['facts']
        dup = sorted({f for f in seen if seen.count(f) > 1})
        if dup:
            bad.append('the matrix places %s more than once' % ', '.join(dup))
        missing = sorted(ids - set(seen))
        if missing:
            bad.append('the matrix leaves out %s; every fact is placed in both arrangements'
                       % ', '.join(missing))
    for i, c in enumerate(l['conclusions']):
        bad += check_unit(c, 'conclusion %d' % (i + 1))
        if PRESCRIPTIVE.search(c['text']):
            bad.append('conclusion %d tells the reader what to do: %r' % (i + 1, c['text']))
        for r in c['rests_on']:
            if r not in ids:
                bad.append('conclusion %d rests on %r, which is not a fact on the page' % (i + 1, r))
    return bad
