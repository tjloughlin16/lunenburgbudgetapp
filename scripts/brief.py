#!/usr/bin/env python3
"""The citizen-first top of a report, and the checks that keep it honest.

A PROTOTYPE OF A PROPOSED STANDARD (notes/process/REPORT-FORMAT.md), used by
/analysis/transportation only until TJ approves it. It sits beside conclusions.py rather
than inside it so that no other report's validation changes while the format is on trial.

WHAT IT IS FOR. Residents told TJ the report tops were hard to parse: a large number, a
paragraph under it, and no sentence anybody could carry out of the room. So the unit here
is the SENTENCE, not the figure, and the page is ordered by DEPTH:

    answer      one or two sentences: what is going on
    chains      one per question a resident actually asks. Each has
                  question   the resident's question, in their words
                  verdict    sound / concern / problem / unknown
                  say        THE sentence to repeat, true as worded and without context
                  steps      what that sentence rests on, each one a layer deeper than the
                             last, ending at a section of the evidence or at a gap and the
                             document that would close it

THE PAGE INFORMS; THE READER DECIDES. TJ, 10 October 2026, removing a "what to ask the School
Committee" block from the first draft: *"the information needs to be clear enough that anyone
can understand it and repeat the words if they care enough, and advocate if they want. but
this is too much on the nose."* So there are no asks and no recommendations here, and
REGISTER is checked: a unit that tells the reader what to do or what anybody should do is
refused. What is not yet known is not a to-do list either -- it is the last layer of the
chain it belongs to, a `gap`, with the document that would settle it.

Every piece of prose is a UNIT: its text, the figures it states (built by
conclusions.figure), and any literals (statute names, account codes, dates that are not
derived). The same rule-2 check conclusions.py runs is run on every unit: strip the
registered renderings and the literals, and fail on any digit left standing; fail on any
registered figure the text does not use.

WHY THE CHARACTER BUDGETS ARE WHAT THEY ARE. The top renders in a single column of
`max-w-3xl`, 768px. On a phone it is 400px less a 16px gutter each side, 368px.

  say       17px semibold, mean advance about 0.53em, so about 9px a character: 85 a line
            on a laptop, 41 on a phone. 150 is two lines on a laptop and four on a phone,
            which is as long as a sentence can be and still be said aloud in one breath.
  question  13px, one line on a laptop: 70.
  answer    19px, about 10px a character, 76 a line: 260 is three and a half lines on a
            laptop. Longer than that and it is a paragraph of context, which rule 7a bans.
  step      14.5px, about 7.4px a character, less a 12px indent per layer: about 95 a line
            at the deepest layer. 220 is two and a half lines -- one measured thing.
  closes    13px: 150, under two lines -- the document that would settle a gap.

They are set from the width, and the build fails past them -- rule 7b, "enforce the length
in the generator, not by eye".
"""
import re

from conclusions import ConclusionError, figure  # noqa: F401  (figure is re-exported)

VERDICTS = ('sound', 'concern', 'problem', 'unknown')
# The words a reader sees. Each names the result of a COMPARISON -- the measured thing set
# against what it was supposed to equal -- and never a judgement of anybody (rule 8).
LABEL = {'sound': 'Matches', 'concern': 'Mixed picture', 'problem': 'Does not match',
         'unknown': 'Can’t tell yet'}

# Advocacy and instruction, refused in every unit. The page states what is true; whether
# to act on it is the reader's business.
PRESCRIPTIVE = re.compile(r"\b(should|must|ought|push(?:es|ed)? for|ask(?:s|ed)? for|"
                          r"needs? to|have to|has to|demand|urge|call on|it is time)\b", re.I)
# What KIND of statement a step is. Rule 7 in a field: a measurement, a quotation from the
# record, a caption we could only locate, our own estimate, a cause offered as a hypothesis,
# or the point where the data stops and a document would have to take over.
KINDS = ('measured', 'quote', 'caption', 'estimate', 'hypothesis', 'gap')

ANSWER_MAX = 260
QUESTION_MAX = 70
SAY_MAX = 150
STEP_MAX = 220
CLOSES_MAX = 150
CHAINS = (3, 6)          # fewer than three is not a picture; more than six is a list
STEPS = (2, 5)           # a sentence with one reason under it is a card; five is a report

ID_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def _unit(text, figures=None, allow=(), cap=None, name='text'):
    if not isinstance(text, str) or not text.strip():
        raise ConclusionError('%s is empty' % name)
    text = ' '.join(text.split())
    if cap and len(text) > cap:
        raise ConclusionError(
            '%s is %d characters and the budget is %d: %r. A sentence that needs more is '
            'carrying two ideas; put the second one a layer down.' % (name, len(text), cap, text))
    figures = dict(figures or {})
    for k, v in figures.items():
        if not (isinstance(v, dict) and set(v) == {'value', 'text', 'unit'}):
            raise ConclusionError('%s: figures[%r] was not built by figure()' % (name, k))
    return {'text': text, 'figures': figures, 'literals': list(allow)}


def check_unit(u, where):
    """Rule 2 on one unit: every registered figure appears, and no digit is unregistered."""
    bad = []
    for k, f in sorted(u['figures'].items()):
        if f['text'] not in u['text']:
            bad.append('%s: figure %r renders as %r and the text does not contain it'
                       % (where, k, f['text']))
    # The `closes` line is prose that ships too, so it is held to the same rule.
    residue = u['text'] + ' ' + u.get('closes', '')
    for t in sorted([f['text'] for f in u['figures'].values()] + list(u['literals']),
                    key=len, reverse=True):
        residue = residue.replace(t, ' ')
    left = sorted(set(re.findall(r'\d[\d,.]*', residue)))
    if left:
        bad.append('%s: %s appear and are not registered figures or declared literals: %r'
                   % (where, ', '.join(repr(x) for x in left), u['text']))
    return bad


def step(text, kind, figures=None, allow=(), link=None, closes=None, cite=None):
    """One layer of a chain. `link` is (anchor, label): the section of the page's evidence
    this layer rests on. `cite` is (href, label): a source outside the page -- a minute, a
    video at a timestamp. A `gap` names the document that would close it in `closes`."""
    if kind not in KINDS:
        raise ConclusionError('step kind %r is not one of %s' % (kind, KINDS))
    u = _unit(text, figures, allow, STEP_MAX, 'step')
    u['kind'] = kind
    if kind == 'gap' and not closes:
        raise ConclusionError('a gap step must say what would close it: %r' % text)
    if closes:
        u['closes'] = ' '.join(closes.split())
        if len(u['closes']) > CLOSES_MAX:
            raise ConclusionError('closes is %d characters, budget %d: %r'
                                  % (len(u['closes']), CLOSES_MAX, closes))
    if link:
        u['link'] = {'anchor': link[0], 'label': link[1]}
    if cite:
        u['cite'] = {'href': cite[0], 'label': cite[1]}
    if kind == 'caption' and not cite:
        raise ConclusionError('a caption step must cite the video at its timestamp: %r' % text)
    return u


def chain(id, question, verdict, say, steps, figures=None, allow=()):
    if not ID_RE.match(id or ''):
        raise ConclusionError('chain id %r is not a slug' % (id,))
    if verdict not in VERDICTS:
        raise ConclusionError('%s: verdict %r is not one of %s' % (id, verdict, VERDICTS))
    q = ' '.join(question.split())
    if len(q) > QUESTION_MAX or not q.endswith('?'):
        raise ConclusionError('%s: the question must be a question of at most %d characters: %r'
                              % (id, QUESTION_MAX, q))
    if not STEPS[0] <= len(steps) <= STEPS[1]:
        raise ConclusionError('%s: %d steps; a chain has %d to %d' % ((id, len(steps)) + STEPS))
    last = steps[-1]
    if not (last.get('link') or last['kind'] == 'gap'):
        raise ConclusionError('%s: the deepest step must end at the evidence (link=) or at a '
                              'gap and the document that would close it' % id)
    if verdict == 'unknown' and not any(s['kind'] == 'gap' for s in steps):
        raise ConclusionError('%s: a "can’t tell" verdict must name the gap that stops it' % id)
    s = _unit(say, figures, allow, SAY_MAX, '%s say' % id)
    return dict(id=id, question=q, verdict=verdict, label=LABEL[verdict], say=s,
                steps=steps)


def brief(answer, chains, answer_figures=None, answer_allow=()):
    """Validate the whole top and return it ready for a payload. Refuses rather than warns."""
    a = _unit(answer, answer_figures, answer_allow, ANSWER_MAX, 'answer')
    if not CHAINS[0] <= len(chains) <= CHAINS[1]:
        raise ConclusionError('%d chains; the top holds %d to %d' % ((len(chains),) + CHAINS))
    ids = [c['id'] for c in chains]
    if len(set(ids)) != len(ids):
        raise ConclusionError('two chains share an id')
    out = dict(answer=a, chains=chains)
    bad = check(out)
    if bad:
        raise ConclusionError('the brief did not pass:\n  ' + '\n  '.join(bad))
    return out


def units(b):
    """Every unit of prose in a brief, with where it sits -- for the check and for a
    verifier that wants to recompute each figure."""
    yield 'answer', b['answer']
    for c in b['chains']:
        yield '%s/say' % c['id'], c['say']
        for i, s in enumerate(c['steps']):
            yield '%s/step%d' % (c['id'], i + 1), s


def check(b):
    bad = []
    for where, u in units(b):
        bad += check_unit(u, where)
        for t in (u['text'], u.get('closes', '')):
            hit = PRESCRIPTIVE.search(t)
            if hit:
                bad.append('%s: %r tells the reader what to do; state what is true instead: %r'
                           % (where, hit.group(0), t))
    for c in b['chains']:
        for t in (c['question'],):
            if PRESCRIPTIVE.search(t):
                bad.append('%s: the question is prescriptive: %r' % (c['id'], t))
    return bad
