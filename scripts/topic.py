#!/usr/bin/env python3
"""ONE TOPIC PAGE, validated. The payload every topic generator emits and Topic.tsx renders.

A topic answers one question in under five minutes (scripts/topics.py has the model). Its
parts, in reading order:

    title       from the registry -- descriptive, two to four words, never typed here
    finding     ONE line: what the page shows. The line under the title on the shelf too
    chart       the page's SIGNATURE: the one picture a reader remembers it by. Built with
                series(), ranking(), parts() or image() below -- a few lines of Python,
                drawn by one component (fy28/src/components/TopicCharts.tsx). The older
                form, {id, source} naming a bespoke component in ANALYSIS_CHARTS, still
                works and is for charts nothing here can draw.
    facts       tiles (ladder.fact): a value and a label carrying its unit, with its kind
    conclusions two to four (ladder.conclusion), each naming the facts it rests on, and
                optionally `notes`: brief.step layers -- what is not known, a hypothesis, a
                link to the evidence. Only those three render; the facts carry the rest
    table       optional: FigureTable data -- the figures behind the chart
    said        optional: what was said in public meetings ABOUT THIS TOPIC ONLY
    sources     where the figures come from, by address

Every unit of prose goes through the same rule-2 check the brief and the ladder use
(brief.check_unit): a digit that is not a registered figure or a declared literal refuses
the page. The budgets are the ladder's: a finding is a conclusion's length, 110.

CHARTS -- THE BRIEF FOR A CATEGORY AGENT. TJ, 13 October 2026: "Every topic page should have
some defining chart OR image if the data doesnt represent well by a chart."

    from topic import series, track, ranking, parts, image

    chart=series('Parks vote by year', [C.fy(y) for y in years], [
        track('Voted, Finance Committee workbook', [gl[y] for y in years], 'stated', 'bar'),
        track('At the levy limit from FY2010', path, 'estimate', 'line')], '$')
    chart=ranking('Grounds bid by park', [(r['park'], r['year_one']) for r in rows], '$',
                  highlight='Marshall Park', basis='stated')
    chart=parts('Who paid for registrations', [('Residents', a), ('Non-residents', b)], '$')
    chart=image('/docs/.../page-12.png', alt='...', caption='...')

  series   one to five named tracks over years or categories, as lines or bars (a track may
           override the chart's mark, so bars and a line can share an axis). None is a GAP
           and is drawn as one -- never pass 0 for a year nobody printed. `stacked=True`
           stacks the bar tracks: use it when the tracks are parts of one total, or when
           they cover DIFFERENT years (a workbook series and a ledger point), so one bar
           stands per year.
  ranking  horizontal bars, sorted largest first, `highlight` marking the row(s) the page is
           about -- Lunenburg among towns, one park among six. `stack=[names]` with a list of
           values per row splits each bar (residents and non-residents of each programme).
  parts    shares of ONE whole, as a single bar split into its parts -- "9 of 16 boards".
           Never a pie. Two to six parts, all positive, and they must BE the whole: the
           helper does not invent a remainder.
  bridge   a WATERFALL: one total stepped to another in signed, labelled pieces, drawn in
           the order given -- last year's surplus, plus the budget's rise, less each kind
           of spending's, to this year's. The helper refuses pieces that do not add up to
           the end: a bridge with a remainder is not a bridge.
  image    for a topic the numbers do not draw well -- a crop of the source page, a diagram.
           src is an address the site serves (fy28/public, or /docs/<key> in the archive
           manifest); alt and caption are required.

  `basis` is rule 3 on the picture: 'published' (a record printed it), 'stated' (a person
  assembled it, rule 13a -- marked "not from the books"), 'estimate' (ours -- drawn dashed
  and amber-edged, and labelled). One chart may mix them, one per track.
  `unit` is '$', '%' (values are percents: 12.5 means 12.5%), 'count', or a plural noun
  ('registrations', 'passes'). A chart without a unit is the bare `10` rule 7b forbids.
  Every value is also written out as a display string by fmt() -- the same C.usd / C.pct /
  C.num the prose uses -- and the page shows those strings, so a bar's label and the sentence
  beside it cannot round one figure two ways. Pass raw numbers; never pre-round to match.
  `note` is one line under the chart, held to rule 2 like every other sentence (figures=,
  allow=). The chart TITLE is a 2-8 word noun phrase with no digits: the figures are in
  the chart, and a number in a title is prose nothing checks.

  PICKING IT. The signature is the page's ARGUMENT drawn, not its first table column: the
  parks spending page draws voted, final budget and spent on one axis, because the finding
  is the gap between them. Ask what the finding compares -- over time (series), against
  others (ranking), or within a whole (parts) -- and draw that. Values are read from the data
  the generator already holds; a typed number is refused by review, not by this module.
  Use image when the thing IS a document (a bid sheet's layout, a printed table nobody
  reconciled) or when there are fewer than two numbers to draw.

  CHART_REQUIRED, below, is False until every category is converted; then page() refuses a
  topic with no chart.
"""
import math
import os
import re

from brief import _unit, check_unit, PRESCRIPTIVE
import conclusions as _C
from conclusions import ConclusionError
import ladder as LD
import topics as REG

FINDING_MAX = 110
# A PAGE THAT IS TOO LONG IS TWO PAGES. TJ, 12 October 2026: "it's an indicator that we
# didn't hub and spoke it enough if the final reports are still too long." So length is
# not tuned by trimming prose: past these, the build refuses, and the remedy is to split the
# topic in the registry. Set just above the longest page on the day they were written.
TOPIC_WORDS_MAX = 320     # prose a reader meets: finding, labels, conclusions, notes, quotes
HUB_WORDS_MAX = 400
TABLE_ROWS_MAX = 30
FACTS = (2, 12)
CONCLUSIONS = (1, 4)
SAID_MAX = 4


def ledger(caption, note, cards):
    """A LEFTOVER, ACCOUNT BY ACCOUNT: one card per account, its evidence folding out (drawn by
    fy28/src/components/AccountLedger.tsx). cards: dicts with id, label, account, left (text),
    shape (one line, words only), figures [(label, text)], sections [dict(title, columns, rows
    [(label, [cells])], note)], quotes [dict(quote, label, href)] -- each already checked verbatim
    by the generator -- unknown and closes (rule 7c: what the card cannot show, and what would
    settle it). Every figure is formatted by the generator; the component formats nothing."""
    out = []
    for c in cards:
        out.append(dict(
            id=c['id'], label=c['label'], account=c['account'], left=c['left'], shape=c['shape'],
            figures=[dict(label=l, text=t) for l, t in c['figures']],
            sections=[dict(title=s['title'], columns=list(s['columns']),
                           rows=[dict(label=l, cells=list(cells)) for l, cells in s['rows']],
                           **({'note': s['note']} if s.get('note') else {}))
                      for s in c['sections'] if s['rows']],
            quotes=list(c.get('quotes', ())), unknown=c['unknown'], closes=c['closes'],
            open=bool(c.get('open'))))
    return dict(caption=caption, note=note, cards=out)


def _ledger_bad(l, where):
    bad = []
    if not l['cards']:
        bad.append('%s: a ledger with no cards' % where)
    for c in l['cards']:
        w = '%s card %r' % (where, c['label'])
        for k in ('label', 'account', 'left', 'shape', 'unknown', 'closes'):
            if not str(c.get(k) or '').strip():
                bad.append('%s: no %s' % (w, k))
        if not c['closes'].strip():
            bad.append('%s: says nothing about what would settle it -- rule 7c' % w)
        for s in c['sections']:
            if len(s['rows']) > TABLE_ROWS_MAX:
                bad.append('%s section %r: past %d rows' % (w, s['title'], TABLE_ROWS_MAX))
            if any(len(r['cells']) != len(s['columns']) for r in s['rows']):
                bad.append('%s section %r: a row with the wrong number of cells' % (w, s['title']))
        for q in c['quotes']:
            if set(q) != {'quote', 'label', 'href'} or not _served(q['href']):
                bad.append('%s: a quotation without a served source' % w)
    return bad


def check_ledger(l, where):
    bad = _ledger_bad(l, where)
    if bad:
        raise ConclusionError('ledger did not pass:\n  %s' % '\n  '.join(bad))
    return l


def page(id, finding, facts, conclusions, chart=None, table=None, said=(), sources=(),
         finding_figures=None, finding_allow=(), draft=None, also=()):
    """`draft`: {'title', 'home'} for a page NOT YET in the registry -- an auto-generated draft
    (scripts/generate_report.py). Every check below runs on it exactly as on a registered page;
    only the title and the shelf come from the draft instead of scripts/topics.py.

    `also`: up to two more charts, drawn under the signature, for a second question the same
    figures answer -- a stack says what a total is made of, small multiples how each part
    moved. The signature stays first and stays the page's one remembered image."""
    if draft:
        title, home = draft['title'], draft['home']
        if not any(c['id'] == home for c in REG.CATEGORIES):
            raise ConclusionError('draft %r: home %r is not a category in scripts/topics.py' % (id, home))
        if title.rstrip().endswith(('?', '.')) or len(title.split()) > 5:
            raise ConclusionError('draft %r: title %r reads as a sentence' % (id, title))
    elif id not in REG.TOPICS:
        raise ConclusionError('topic %r is not in scripts/topics.py' % id)
    else:
        title, home, _ = REG.TOPICS[id]
    f = _unit(finding, finding_figures, finding_allow, FINDING_MAX, '%s finding' % id)
    if not FACTS[0] <= len(facts) <= FACTS[1]:
        raise ConclusionError('%s: %d facts; a topic holds %d to %d' % ((id, len(facts)) + FACTS))
    if not CONCLUSIONS[0] <= len(conclusions) <= CONCLUSIONS[1]:
        raise ConclusionError('%s: %d conclusions; a topic holds %d to %d'
                              % ((id, len(conclusions)) + CONCLUSIONS))
    if len(said) > SAID_MAX:
        raise ConclusionError('%s: %d quotations; a topic quotes at most %d -- the rest stay in '
                              'the full report' % (id, len(said), SAID_MAX))
    ids = [x['id'] for x in facts]
    if len(set(ids)) != len(ids):
        raise ConclusionError('%s: two facts share an id' % id)
    bad = check_unit(f, '%s finding' % id)
    bad += check_chart(chart, id, required=CHART_REQUIRED)
    if len(also) > 2:
        bad.append('%s: %d extra charts; a topic draws its signature and at most two more'
                   % (id, len(also)))
    for i, c in enumerate(also):
        bad += check_chart(c, '%s also %d' % (id, i + 1), required=True)
    for x in facts:
        bad += check_unit(x['label'], '%s %s label' % (id, x['id']))
    for i, c in enumerate(conclusions):
        bad += check_unit(c, '%s conclusion %d' % (id, i + 1))
        for r in c['rests_on']:
            if r not in ids:
                bad.append('%s conclusion %d rests on %r, not a fact on this page' % (id, i + 1, r))
        for n in c.get('notes', []):
            bad += check_unit(n, '%s conclusion %d note' % (id, i + 1))
        if PRESCRIPTIVE.search(c['text']):
            bad.append('%s conclusion %d tells the reader what to do' % (id, i + 1))
    if not sources:
        bad.append('%s: no sources -- rule 12' % id)
    n = _words([f] + [x['label'] for x in facts] + list(conclusions)
               + [nn for c in conclusions for nn in c.get('notes', [])]
               + [dict(text=q['quote']) for q in said])
    if n > TOPIC_WORDS_MAX:
        bad.append('%s: %d words of prose, the limit is %d -- this is two topics; split it in '
                   'the registry rather than trimming it' % (id, n, TOPIC_WORDS_MAX))
    if table and any(len(v['rows']) > TABLE_ROWS_MAX for v in table['views']):
        bad.append('%s: a table runs past %d rows -- split it by period or by group'
                   % (id, TABLE_ROWS_MAX))
    for v in (table or {}).get('views', []):
        for r in v['rows']:
            m = r.get('marks')
            if m is not None and (len(m) != len(r['cells']) or any(x not in (1, -1, None) for x in m)):
                bad.append('%s: table %r row %r: marks must be 1, -1 or None, one per cell -- '
                           'build them with change_marks()' % (id, v['key'], r['label']))
    if bad:
        raise ConclusionError('topic %s did not pass:\n  %s' % (id, '\n  '.join(bad)))
    extra = dict(also=list(also)) if also else {}   # absent, not empty: no other payload moves
    return dict(
        extra, id=id, kind='topic', title=title, category=home,
        path=('/%s/%s' % (home, id)) if draft else REG.path(id),
        shelves=[home] if draft else REG.shelves_of(id), finding=f, chart=chart, facts=list(facts),
        conclusions=list(conclusions), table=table, said=list(said), sources=list(sources),
        full_report=_full(home))


def _words(units):
    return sum(len(u['text'].split()) for u in units)


def conclusion(text, rests_on, figures=None, allow=(), notes=()):
    """A topic conclusion: ladder.conclusion plus `notes`, the brief.step layers under it."""
    c = LD.conclusion(text, rests_on, figures, allow)
    if notes:
        c['notes'] = list(notes)
    return c


# ---------------------------------------------------------------------------- charts
# The module docstring is the brief. Every helper returns a plain dict the page renders with
# fy28/src/components/TopicCharts.tsx, and check_chart() re-validates it inside page() and
# hub(), so a dict built by hand passes the same gate or none.

CHART_REQUIRED = True     # every topic and hub carries one -- TJ, 13 October 2026
CHART_TYPES = ('series', 'ranking', 'parts', 'bridge', 'image')
BRIDGE_STEPS = (2, 10)
BASES = ('published', 'stated', 'estimate')
MARKS = ('line', 'bar')
CHART_TITLE_WORDS = (2, 8)
CHART_NOTE_MAX = 160
CAPTION_MAX = 220
ALT = (20, 300)
TRACKS_MAX = 5            # the site's validated categorical set has five hues; never cycle
PANELS_MAX = 16           # small multiples: each panel is LABELLED, so a colour may repeat --
                          # but only on purpose, as the band of another chart it belongs to
POINTS_MAX = 40
ROWS_MAX = 20             # a ranking past twenty is a table. Was 15; raised 14 Oct 2026 so the
                          # 18 Monty Tech member towns can be ranked with Lunenburg highlighted
PARTS = (2, 8)            # past five parts the palette runs out: `highlight` is then required
LABEL_MAX = 48
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PUBLIC = os.path.join(_ROOT, 'fy28', 'public')


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _title_bad(t, where):
    if not isinstance(t, str) or not t.strip():
        return ['%s: a chart needs a title' % where]
    t = ' '.join(t.split())
    bad = []
    if not CHART_TITLE_WORDS[0] <= len(t.split()) <= CHART_TITLE_WORDS[1]:
        bad.append('%s: chart title %r is %d words; a title is a %d-%d word noun phrase'
                   % ((where, t, len(t.split())) + CHART_TITLE_WORDS))
    if t.endswith(('?', '.', '!')) or ': ' in t:
        bad.append('%s: chart title %r reads as a sentence -- name the subject, the finding '
                   'is the line above the chart' % (where, t))
    if re.search(r'\d', re.sub('|'.join(map(re.escape, TITLE_NAMES)), '', t)):
        bad.append('%s: chart title %r carries a figure; a number in a title is prose nothing '
                   'checks -- put it in the note' % (where, t))
    return bad


# A NAME IS NOT A FIGURE. "Chapter 70" is what the state calls its school aid, and a title
# that cannot say it reads "formula aid" -- a word nobody searches for.
TITLE_NAMES = ('Chapter 70',)


def _unit_bad(u, where):
    if u in ('$', '%', 'count'):
        return []
    if (isinstance(u, str) and 0 < len(u) <= 24 and not re.search(r'\d', u)
            and u == u.strip() and u.lower() == u):
        return []
    # An initialism a reader meets in the prose (FTE) is a unit too; a capitalised word is not.
    if isinstance(u, str) and re.fullmatch(r'[A-Z]{2,5}', u):
        return []
    return ['%s: unit %r is not $, %%, count, a short lower-case noun (\'registrations\') or an initialism (FTE)'
            % (where, u)]


def _label_bad(s, where, what):
    if not isinstance(s, str) or not s.strip():
        return ['%s: a %s is empty' % (where, what)]
    if len(s) > LABEL_MAX:
        return ['%s: %s %r is %d characters, budget %d' % (where, what, s, len(s), LABEL_MAX)]
    return []


def _note(note, figures, allow, cap, name):
    return _unit(note, figures, allow, cap, name) if note else None


def track(name, values, basis='published', mark=None, colour=None):
    """One named line or set of bars in series(). `values` are numbers or None (a gap).
    `colour`: the track's place in the palette when it must match another chart that draws
    the same thing in a different order -- written only when set."""
    t = dict(name=' '.join(str(name).split()), values=list(values), basis=basis, mark=mark)
    if colour is not None:
        t['colour'] = int(colour)
    return t


def series(title, x, tracks, unit, kind='line', stacked=False, note=None, note_figures=None,
           note_allow=(), decimals=None, reference=None, from_zero=True, multiples=False):
    """Named tracks over the same x -- years (C.fy(y)) or categories, as strings.
    reference: (value, label) -- one horizontal line a reader measures the tracks against,
      e.g. (100, 'The state minimum'). Its value is shown by fmt(), like every other.
    from_zero: False lets a LINE chart's axis start near its data, for ratios that move
      within a few points. Refused with bars: a bar's length IS its value, and a bar
      drawn from 90 overstates every difference.
    multiples: SMALL MULTIPLES -- one small panel per track, every panel on the same scale
      from zero, so each track's own change can be read and their sizes still compare. The
      answer to a stack, where only the bottom band sits on a flat baseline (TJ, 19 October
      2026: "Its hard with the stacking to see how each one ITSELF changed")."""
    if multiples and (stacked or not from_zero or reference is not None):
        raise ConclusionError('chart %r: small multiples are unstacked, from zero, with no '
                              'reference line -- one shared scale is the point' % title)
    if not from_zero and any((t['mark'] or kind) == 'bar' for t in tracks):
        raise ConclusionError('chart %r: from_zero=False with bars -- a bar is measured from zero'
                              % title)
    ref = None
    if reference is not None:
        rv, rl = reference
        ref = dict(value=rv, label=' '.join(str(rl).split()), text=fmt(unit, rv, decimals))
    # `multiples` is written only when set, so no existing chart's payload changes.
    return _checked(dict(type='series', title=' '.join(title.split()), unit=unit, kind=kind,
                         stacked=bool(stacked), x=list(x),
                         series=[dict(t, mark=t['mark'] or kind) for t in tracks],
                         decimals=decimals, reference=ref, from_zero=bool(from_zero),
                         note=_note(note, note_figures, note_allow, CHART_NOTE_MAX, 'chart note'),
                         **({'multiples': True} if multiples else {})))


def ranking(title, rows, unit, highlight=(), basis='published', stack=None, note=None,
            note_figures=None, note_allow=(), decimals=None):
    """Horizontal bars, largest first. rows: [(label, value)], or with `stack` (a list of
    names) [(label, [value per name])]. `highlight`: a label or labels to mark."""
    hl = [highlight] if isinstance(highlight, str) else list(highlight)
    total = lambda v: (sum(x for x in v if _isnum(x)) if isinstance(v, (list, tuple)) else v)
    rs = [dict(label=l, values=list(v)) if stack else dict(label=l, value=v) for l, v in rows]
    rs.sort(key=lambda r: (total(r.get('values', r.get('value'))) is None,
                           -(total(r.get('values', r.get('value'))) or 0)))
    return _checked(dict(type='ranking', title=' '.join(title.split()), unit=unit, basis=basis,
                         rows=rs, stack=list(stack) if stack else None, highlight=hl,
                         decimals=decimals, note=_note(note, note_figures, note_allow, CHART_NOTE_MAX, 'chart note')))


def parts(title, items, unit, basis='published', note=None, note_figures=None, note_allow=(),
          decimals=None, highlight=None):
    """Shares of ONE whole, drawn as a single split bar. items: [(label, value)], in the
    order to draw them. The parts must BE the whole; nothing here adds a remainder.
    `highlight`: the one part the page is about -- drawn in colour, every other part in a
    neutral shade, so the eye lands on it (TJ, 20 October 2026: what was LEFT, as a slice).
    Written only when set, so no existing chart's payload changes."""
    extra = {'highlight': highlight} if highlight is not None else {}
    return _checked(dict(type='parts', title=' '.join(title.split()), unit=unit, basis=basis,
                         parts=[dict(label=l, value=v) for l, v in items],
                         decimals=decimals, note=_note(note, note_figures, note_allow, CHART_NOTE_MAX, 'chart note'),
                         **extra))


def bridge(title, start, steps, end, unit, basis='published', note=None, note_figures=None,
           note_allow=(), decimals=None):
    """A waterfall. start and end: (label, total); steps: [(label, signed change)], drawn in
    the order given. The steps must carry start to end to the cent."""
    return _checked(dict(type='bridge', title=' '.join(title.split()), unit=unit, basis=basis,
                         start=dict(label=start[0], value=start[1]),
                         steps=[dict(label=l, value=v) for l, v in steps],
                         end=dict(label=end[0], value=end[1]), decimals=decimals,
                         note=_note(note, note_figures, note_allow, CHART_NOTE_MAX, 'chart note')))


def change_marks(values, pairs, threshold):
    """MARKS FOR A TABLE ROW: which cells moved by at least `threshold` against the cell they are
    compared with. values: the row's numbers, in column order (None where there is none);
    pairs: [(column, compared_with)], e.g. [(1, 0), (2, 1), (3, 2)] for consecutive years.
    Returns one entry per column: 1 (rose), -1 (fell) or None. The generator decides; the
    table only draws a mark beside the cell (TJ, 20 October 2026: an icon "for when the diff
    between years is 10k or above (positive OR negative)")."""
    out = [None] * len(values)
    for i, j in pairs:
        a, b = values[i], values[j]
        if a is None or b is None:
            continue
        if abs(a - b) >= threshold:
            out[i] = 1 if a > b else -1
    return out


def image(src, alt, caption, caption_figures=None, caption_allow=()):
    """A picture where the numbers do not draw: a crop of the source page, a diagram."""
    return _checked(dict(type='image', src=src, alt=' '.join(str(alt).split()),
                         caption=_unit(caption, caption_figures, caption_allow, CAPTION_MAX,
                                       'image caption')))


def _checked(c):
    bad = _inline_bad(c, 'chart', texts=False)
    if bad:
        raise ConclusionError('chart did not pass:\n  %s' % '\n  '.join(bad))
    c.update(_texts(c))
    return c


def fmt(unit, v, decimals=None):
    """A chart value as text, by the SAME formatters the prose uses -- so a bar's label and
    the sentence beside it cannot round one figure two ways (rule 2: nothing downstream
    reformats). The page shows these strings; only axis ticks are formatted in the browser."""
    if v is None:
        return None
    if unit == '$':
        # Whole dollars unless the chart declares `decimals`: a fee of $568.75 drawn as "$569"
        # beside a sentence that says $568.75 is one figure rounded two ways.
        if decimals is None:
            return _C.usd(v)
        return ('-$' if v < 0 else '$') + format(abs(v), ',.%df' % decimals)
    # `decimals` is the chart's own declaration (series/ranking/parts take it), so a bar
    # can read 6.84% or 1.0 FTE exactly as the prose beside it does. Without it: whole
    # numbers bare, anything else to one place.
    if unit == '%':
        return _C.pct(v, decimals if decimals is not None else 0 if float(v).is_integer() else 1)
    n = (format(v, ',.%df' % decimals) if decimals is not None
         else _C.num(v) if float(v).is_integer() else format(v, ',.1f'))
    return n if unit == 'count' else '%s %s' % (n, unit)


def _texts(c):
    """The display strings for every value in a chart, keyed beside the values."""
    u, t, d = c.get('unit'), c['type'], c.get('decimals')
    if t == 'series':
        def one(s):
            o = dict(s, texts=[fmt(u, v, d) for v in s['values']])
            # A small-multiples panel prints its own change, first value to last, written here
            # so the browser formats nothing (rule 2).
            if c.get('multiples'):
                got = [v for v in s['values'] if v is not None]
                ch = got[-1] - got[0]
                o['change'] = ('+' if ch >= 0 else '-') + fmt(u, abs(ch), d)
            return o
        return dict(series=[one(s) for s in c['series']])
    if t == 'ranking':
        def one(r):
            vs = r['values'] if c['stack'] else [r['value']]
            got = [v for v in vs if v is not None]
            texts = [fmt(u, v, d) for v in vs]
            return dict(r, texts=texts, total=(texts[0] if not c['stack'] else
                                               fmt(u, round(sum(got), 6), d) if got else None))
        return dict(rows=[one(r) for r in c['rows']])
    if t == 'parts':
        whole = round(sum(p['value'] for p in c['parts']), 2)
        return dict(total=fmt(u, whole, d), parts=[
            dict(p, text=fmt(u, p['value'], d), share=_C.pct(100.0 * p['value'] / whole, 0))
            for p in c['parts']])
    if t == 'bridge':
        signed = lambda v: ('+' if v >= 0 else '-') + fmt(u, abs(v), d)
        # `after`: the running total once the step is taken -- the number a floating bar's
        # POSITION encodes, printed so nobody has to read it off the axis (TJ, 20 October
        # 2026: "lets try to make this more clear how to read it").
        run, steps = c['start']['value'], []
        for x in c['steps']:
            run += x['value']
            steps.append(dict(x, text=signed(x['value']), after=fmt(u, round(run, 2), d)))
        return dict(start=dict(c['start'], text=fmt(u, c['start']['value'], d)),
                    end=dict(c['end'], text=fmt(u, c['end']['value'], d)), steps=steps)
    return {}


def _served(src):
    if not isinstance(src, str) or not src.startswith('/') or '..' in src:
        return False
    if os.path.exists(os.path.join(_PUBLIC, src.lstrip('/'))):
        return True
    if src.startswith('/docs/'):
        import csv
        man = os.path.join(_ROOT, 'sources', 'data', 'archive-manifest.csv')
        return any(r['key'] == src[len('/docs/'):] for r in csv.DictReader(open(man, encoding='utf-8')))
    return False


def _inline_bad(c, where, texts=True):
    t = c.get('type')
    if t not in CHART_TYPES:
        return ['%s: chart type %r is not one of %s' % (where, t, CHART_TYPES)]
    bad = []
    if texts:
        try:
            ok = all(c.get(k) == v for k, v in _texts(c).items())
        except (KeyError, TypeError):
            ok = False
        if not ok:
            return ['%s: its display strings are missing or do not match its values -- build it '
                    'with series/ranking/parts/image, never by hand' % where]
    if t == 'image':
        if not _served(c.get('src')):
            bad.append('%s: image %r is not served by the site (fy28/public, or /docs/<key> in '
                       'the archive manifest)' % (where, c.get('src')))
        if not ALT[0] <= len(c.get('alt') or '') <= ALT[1]:
            bad.append('%s: alt text is %d characters; it must say what the picture shows, '
                       '%d-%d' % ((where, len(c.get('alt') or '')) + ALT))
        return bad + check_unit(c['caption'], '%s caption' % where)
    bad += _title_bad(c.get('title'), where) + _unit_bad(c.get('unit'), where)
    if c.get('note'):
        bad += check_unit(c['note'], '%s note' % where)
    basis = lambda b, w: [] if b in BASES else ['%s: basis %r is not one of %s' % (w, b, BASES)]
    if t == 'series':
        x, ts = c['x'], c['series']
        if c['kind'] not in MARKS:
            bad.append('%s: kind %r is not one of %s' % (where, c['kind'], MARKS))
        if not 2 <= len(x) <= POINTS_MAX:
            bad.append('%s: %d x values; a series chart draws 2 to %d' % (where, len(x), POINTS_MAX))
        if len(set(x)) != len(x) or not all(isinstance(v, str) and v for v in x):
            bad.append('%s: x must be distinct non-empty strings (C.fy(y) for years)' % where)
        cap = PANELS_MAX if c.get('multiples') else TRACKS_MAX
        if not 1 <= len(ts) <= cap:
            bad.append('%s: %d tracks; a chart holds 1 to %d' % (where, len(ts), cap))
        if len(ts) > TRACKS_MAX and not all('colour' in s for s in ts):
            bad.append('%s: more panels than colours -- give every track its colour= so a '
                       'repeated colour means something' % where)
        if len({s['name'] for s in ts}) != len(ts):
            bad.append('%s: two tracks share a name' % where)
        n = 0
        for s in ts:
            w = '%s track %r' % (where, s['name'])
            bad += _label_bad(s['name'], where, 'track name') + basis(s['basis'], w)
            if s['mark'] not in MARKS:
                bad.append('%s: mark %r is not one of %s' % (w, s['mark'], MARKS))
            if len(s['values']) != len(x):
                bad.append('%s: %d values for %d x' % (w, len(s['values']), len(x)))
            if not all(v is None or _isnum(v) for v in s['values']):
                bad.append('%s: a value is not a number or None' % w)
            k = sum(1 for v in s['values'] if _isnum(v))
            if not k:
                bad.append('%s: no values at all' % w)
            n += k
        if n < 2:
            bad.append('%s: fewer than two numbers -- that is a fact tile, not a chart' % where)
    elif t == 'ranking':
        rs, st = c['rows'], c['stack']
        bad += basis(c['basis'], where)
        if not 2 <= len(rs) <= ROWS_MAX:
            bad.append('%s: %d rows; a ranking draws 2 to %d' % (where, len(rs), ROWS_MAX))
        if len({r['label'] for r in rs}) != len(rs):
            bad.append('%s: two rows share a label' % where)
        if st is not None and not 2 <= len(st) <= TRACKS_MAX:
            bad.append('%s: stack has %d names; 2 to %d' % (where, len(st), TRACKS_MAX))
        for r in rs:
            bad += _label_bad(r['label'], where, 'row label')
            vs = r['values'] if st else [r['value']]
            if st and len(vs) != len(st):
                bad.append('%s row %r: %d values for %d stack names' % (where, r['label'], len(vs), len(st)))
            if not all(v is None or _isnum(v) for v in vs):
                bad.append('%s row %r: a value is not a number or None' % (where, r['label']))
        if sum(1 for r in rs for v in (r['values'] if st else [r['value']]) if _isnum(v)) < 2:
            bad.append('%s: fewer than two numbers' % where)
        for h in c['highlight']:
            if h not in {r['label'] for r in rs}:
                bad.append('%s: highlight %r is not a row' % (where, h))
    elif t == 'parts':
        ps = c['parts']
        bad += basis(c['basis'], where)
        if not PARTS[0] <= len(ps) <= PARTS[1]:
            bad.append('%s: %d parts; a whole splits into %d to %d' % ((where, len(ps)) + PARTS))
        for p in ps:
            bad += _label_bad(p['label'], where, 'part label')
            if not (_isnum(p['value']) and p['value'] > 0):
                bad.append('%s part %r: a part is a positive number' % (where, p['label']))
        if c.get('highlight') is not None and c['highlight'] not in {p['label'] for p in ps}:
            bad.append('%s: highlight %r is not a part' % (where, c['highlight']))
        if len(ps) > 5 and c.get('highlight') is None:
            bad.append('%s: %d parts and five colours -- name the part the page is about with '
                       'highlight=' % (where, len(ps)))
        if c['unit'] == '%':
            bad.append('%s: parts takes the amounts, not percents -- the shares are drawn from '
                       'them' % where)
    elif t == 'bridge':
        st = c['steps']
        bad += basis(c['basis'], where)
        if not BRIDGE_STEPS[0] <= len(st) <= BRIDGE_STEPS[1]:
            bad.append('%s: %d steps; a bridge takes %d to %d' % ((where, len(st)) + BRIDGE_STEPS))
        ends = [c['start'], c['end']]
        for x in ends + st:
            bad += _label_bad(x['label'], where, 'step label')
            if not _isnum(x['value']):
                bad.append('%s step %r: not a number' % (where, x['label']))
        if len({x['label'] for x in ends + st}) != len(st) + 2:
            bad.append('%s: two steps share a label' % where)
        if not bad and abs(c['start']['value'] + sum(x['value'] for x in st)
                           - c['end']['value']) > 0.005:
            bad.append('%s: the steps do not carry %r to %r -- a bridge has no remainder'
                       % (where, c['start']['label'], c['end']['label']))
    return bad


def check_chart(chart, where, required=False):
    """None, the older {id, source} reference, or an inline spec from the helpers above."""
    if chart is None:
        return ['%s: no chart -- every topic draws its signature (topic.py, CHARTS)'
                % where] if required else []
    if not isinstance(chart, dict):
        return ['%s: chart is not a dict' % where]
    if 'type' in chart:
        return _inline_bad(chart, '%s chart' % where)
    if set(chart) == {'id', 'source'}:
        return []
    return ['%s: chart is neither {id, source} nor built by series/ranking/parts/bridge/image' % where]


def hub(cid, answer, ladder, chains=(), chart=None, table=None, answer_figures=None,
        answer_allow=()):
    """A category's hub: the answer, the signature chart, the matrix and conclusions, and --
    added by build_topics_index.py from the registry -- a card per topic."""
    cat = REG.category(cid)
    a = _unit(answer, answer_figures, answer_allow, 260, '%s answer' % cid)
    bad = check_unit(a, '%s answer' % cid)
    bad += check_chart(chart, 'hub %s' % cid, required=CHART_REQUIRED)
    n = _words([a] + [f['label'] for t in ladder['tiers'] for f in t['facts']]
               + ladder['conclusions'])
    if n > HUB_WORDS_MAX:
        bad.append('hub %s: %d words, the limit is %d -- move detail down to a topic'
                   % (cid, n, HUB_WORDS_MAX))
    if bad:
        raise ConclusionError('hub %s did not pass:\n  %s' % (cid, '\n  '.join(bad)))
    return dict(id=cid, kind='hub', title=cat['title'], category=cid, path=REG.path(cid),
                shelves=[cid], answer=a, chart=chart, ladder=ladder, chains=list(chains),
                table=table, full_report=_full(cid))


def _full(cid):
    """The old long report a category came from, if it had one. Not promoted anywhere --
    TJ: "we dont need FULL reports" -- but a note's evidence link may still land in it.

    The long reports are UNLISTED (sources/analyses/UNLISTED), so the link lands on the
    document's published COPY, /docs/analyses/<id>.md -- a serving format, not a door. A
    registry naming anything else (a bespoke page has no /docs copy) gets no link at all."""
    fr = REG.category(cid).get('full_report')
    m = re.match(r'^/analysis/([a-z0-9-]+)$', fr[0]) if fr else None
    return (dict(href='/docs/analyses/%s.md' % m.group(1), label=fr[1]) if m
            else dict(href='', label=''))
