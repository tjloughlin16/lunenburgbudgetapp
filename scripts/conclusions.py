#!/usr/bin/env python3
"""The shape of a CONCLUSION, and the checks that keep one honest.

WHY A CONCLUSION IS A PAYLOAD FIELD AND NOT A SENTENCE IN A PAGE

Every report on this site already computes its figures in a generator and renders them
from a published payload, because rule 2 says a figure typed into prose is the only thing
here that can be silently wrong. The CLAIMS those figures support were exempt from that,
and they should not have been: a claim is prose that ships, it carries figures inside it,
and nothing recomputed it.

So a conclusion is data. The generator that computed the figures writes the sentence that
rests on them, into the same payload, and three things follow that cannot follow from a
sentence in a `.tsx`:

  * the report page RENDERS its conclusions rather than restating them, so a page cannot
    say something its own data no longer supports;
  * the master report at /what-it-all-adds-up-to READS every payload, so a synthesis
    cannot claim more than the reports it synthesises;
  * a verifier can recompute the figures a conclusion names, because they are registered
    beside it rather than buried in the text.

WHAT A CONCLUSION HAS TO BE, and this is the hard half

Rule 8 governs. The job is helping a resident understand what would work and what each
option costs somebody; it is not cataloguing what the town got wrong. A conclusion here
has to explain something the community is ALREADY ARGUING ABOUT, using the data. Everyone
in Lunenburg says special education is expensive and rising; a conclusion tells them what
is actually happening to that money -- where it comes from, what moved, over what period
-- so the argument gets better inputs.

Three things a conclusion is never:

  1. a verdict on anybody's decisions;
  2. a restatement of a figure with no meaning attached ("spending rose 12%" is a
     measurement, not a conclusion);
  3. an explanation the data cannot support -- rule 7: a cause attached to a measurement
     is a HYPOTHESIS, and `kind='hypothesis'` is the only way to say one here.

AND THE FOURTH, WHICH IS THE ONE THAT KEEPS GETTING WRITTEN ANYWAY

**A defect in a DOCUMENT is a footnote, never a conclusion.** An ambiguity, an omission,
an inconsistent label, a figure two sources disagree about -- all of these are true, all
of them are well evidenced, and none of them is what a resident came for. They answer
"what did they get wrong", which rule 8 says is not this project's job.

The test is one question: **is this about the WORLD or about a DOCUMENT?** What the money
does, where it comes from, what changed, what it means for a household or for the town --
world, and it can be a conclusion. Something unclear, missing, inconsistent or badly
labelled -- document, and it belongs in `not_shown`, in the payload's `not_established`,
or as a row in `sources/data/money-gaps.csv`.

TJ, on a drafted conclusion that said a fee cap stated no period and that the two readings
differed by $1,275: *"the conclusions are not the point either... That should be a
footnote, not a big conclusion. That's a focus on the school committee's problems."* The
conclusion that page owed a family was what they will PAY.

The one exception is a documentary limit that changes what a reader should BELIEVE about a
number they are otherwise going to act on -- and even then, lead with the number and its
meaning and set the limit beside it.

This bites hardest exactly where the documents are messiest, because that is where the
temptation is strongest. /what-stopped-being-funded could headline that the budget book
changed shape and lines vanished from it; the conclusion is that a zero is usually a
pause, and most of those lines came back. /monty-tech could headline that rows in the
long series fail their check; the conclusion is that a child moving there moves part of
the town's bill rather than adding to it.

And it must survive "so what". If a reader could answer it with "yes, and?", it is not a
conclusion yet. Nothing in this file can check that; the persona review in
notes/process/PERSONAS.md is what checks it, and it is a person's job.

WHAT THIS FILE DOES CHECK, mechanically

Rule 2, enforced rather than asked for. Every figure a conclusion's text states must be
REGISTERED beside it, with the value it was computed from. `check()` strips the registered
renderings out of the prose and fails if any digit is left standing -- which is the whole
of rule 2 as an assertion rather than an instruction. A statutory name that is not a
derived figure ("Chapter 70", function code 9300) is declared in `allow`, so the exception
is written down and reviewable instead of being invisible.

    from conclusions import conclusion, figure, check

    conclusion(
        id='the-line-is-the-towns-share',
        claim='...',                 one sentence, repeatable at a meeting
        bearing='sizes'|'lever',     does this SIZE a problem, or point at a dial
                                     somebody in Lunenburg can actually turn
        detail='...',                two or three, the support
        figures={'x': figure(39.3, '39.3%')},
        kind='measured',             or 'hypothesis'
        basis='...',                 the documents and series it rests on
        not_shown='...',             the readings that fit the same numbers
    )
"""
import re

KINDS = ('measured', 'hypothesis')

# WHAT A READER CAN DO WITH IT, which is a different axis from whether it is true.
#
# TJ, after reading the synthesis: the conclusions "come off as 'interesting' but not clear
# as to why they are 'important'". This is the distinction he was circling. `kind` says
# whether we measured it or are guessing; `bearing` says whether anybody can act on it.
#
#   sizes   establishes how big something is, or how it got this way. Context. Most
#           conclusions are this and that is fine -- you cannot act on a problem you have
#           not sized.
#   lever   points at something a body in this town can actually decide. A fee, a vote, a
#           schedule, a request. It does NOT say what to decide: rule 8 is that this
#           project names what can be pulled and what it costs somebody, never which to
#           pull.
#
# Optional for now, so the 46 existing conclusions keep building while they are classified
# one report at a time. The master report counts the unclassified out loud, so the gap is
# visible rather than quiet.
BEARINGS = ('sizes', 'lever')

# The keys a conclusion has, in the order they are written. `figure` and `see` are
# optional; everything else is required and empty is a failure, not a default.
KEYS = ('id', 'claim', 'so_what', 'detail', 'figure', 'figures', 'kind', 'bearing',
        'basis',
        'not_shown', 'see', 'literals')

# HOW LONG A CARD'S VISIBLE PROSE MAY BE, and where these two numbers come from.
#
# TJ, reading the synthesis page: *"we cannot have BOLD context lines that are 3-5 lines.
# the metric + the description need to be short. context description should be 1 or 2
# lines max. Additional context must go into the expansion. which means we have to be
# HYPER clear about what the metric represents, and what conclusion to draw from it
# without needing a full paragraph of context for each."*
#
# So a card is exactly four things: the METRIC with its unit, ONE line saying what the
# metric is, ONE line saying what follows from it, and an expansion holding everything
# else. These budgets are the second and third of those, and they are enforced here
# because a rule kept by eye lasts until the next report.
#
# MEASURED, NOT GUESSED. The cards sit in a two-column grid inside `max-w-6xl` -- 1152px,
# less 40px of page padding and a 16px gutter, halved, less 40px of card padding, giving a
# text column of about 528px. The claim is set at 15.5px semibold in the system UI stack,
# whose mean advance is close to 0.53em, so a line holds roughly 64 characters; the
# supporting line is 14px regular at about 0.51em, roughly 74. Two lines of each is 128 and
# 148. The budgets are set BELOW those, at 95 and 110, because a card that exactly fills
# two lines on a 1152px viewport wraps to three on a laptop at 1280 with a scrollbar, and
# because the real constraint is not the pixel -- it is that a sentence needing 128
# characters is carrying two ideas and one of them belongs in the expansion.
CLAIM_MAX = 95
SO_WHAT_MAX = 110

ID_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
DIGIT_RE = re.compile(r'\d')


class ConclusionError(ValueError):
    """A conclusion that would ship a figure nothing computed, or a claim with no basis."""


# A rendering that already says what it is. Everything else needs `unit`.
SELF_EVIDENT = ('$', '%')


def figure(value, text, unit=None):
    """One derived figure: what it is, exactly how the prose renders it, and its UNIT.

    `value` is the number the generator computed -- a verifier recomputes THIS. `text` is
    the string that appears in the claim or the detail, already formatted by the
    generator, because rule 2 means nothing downstream rounds or reformats it.

    `unit` is what the number COUNTS, and it is required of any figure set as a
    conclusion's headline unless the rendering already carries it. TJ, reading the
    synthesis page: *"these metrics on the one big report need units next to them. '10'
    and needing to read the description is hard to understand for instance."*

    That is rule 7 in visual form and not a matter of presentation. Dollars are not
    students, a count is not a rate, and a placement is not a cost -- which is why every
    report on this site states its GRAIN above the fold. A bare `10` in a stat box
    abandons that at the moment a reader is most likely to quote it, and this page sets
    figures from sixteen reports at six different grains side by side: person, dollar,
    placement cohort, town-pair, budget line, fiscal year. Ten children, ten documents and
    ten budget lines are three quantities and must look like three quantities.
    """
    if not isinstance(text, str) or not text.strip():
        raise ConclusionError('a figure must carry the exact text it renders as')
    if unit is not None and (not isinstance(unit, str) or not unit.strip()):
        raise ConclusionError('a unit is a short noun phrase, or it is left out entirely')
    return {'value': value, 'text': text, 'unit': (unit or '').strip()}


def conclusion(id, claim, detail, figures, kind, basis, not_shown, so_what,
               figure=None, see=None, allow=(), no_figure=None, lede=None,
               bearing=None):
    """One conclusion, validated on the way in.

    `figure` names the entry in `figures` to set large above the claim, where the finding
    IS an amount. Where the finding is a relation -- "two sources report different counts
    and cannot be reconciled" -- there is no number to set and it is left out.

    `see` is other pages this conclusion sends a reader to, as `[(slug, label), ...]`.
    Conclusions are plain text on purpose: a sentence that needs a hyperlink inside it to
    make sense is not a sentence anybody can repeat at a meeting.

    `allow` is the declared exceptions to the no-unregistered-digits rule: statute names
    and account codes, which are neither derived nor figures.
    """
    if not ID_RE.match(id or ''):
        raise ConclusionError('conclusion id %r is not a slug' % (id,))
    if bearing is not None and bearing not in BEARINGS:
        raise ConclusionError(
            '%s: bearing=%r is not one of %s. `sizes` establishes how big something is; '
            '`lever` points at something a body in this town can actually decide.'
            % (id, bearing, BEARINGS))
    if kind not in KINDS:
        raise ConclusionError('%s: kind must be one of %s, not %r' % (id, KINDS, kind))
    # `lede` is the long sentence a conclusion used to LEAD with, before the card was cut
    # to a metric and two lines. It is not dropped -- it opens the expansion, where a
    # reader who wants the working finds it, and where every figure it states is still
    # checkable by the rule-2 scan below.
    if lede:
        detail = lede.strip() + ' ' + detail.strip()
    for name, text in (('claim', claim), ('so_what', so_what), ('detail', detail),
                       ('basis', basis), ('not_shown', not_shown)):
        if not isinstance(text, str) or not text.strip():
            raise ConclusionError('%s: %s is empty, and none of the five may be' % (id, name))
    for name, text, cap in (('claim', claim, CLAIM_MAX),
                            ('so_what', so_what, SO_WHAT_MAX)):
        if len(text.strip()) > cap:
            raise ConclusionError(
                '%s: `%s` is %d characters and the card allows %d. Three ideas in a '
                'paragraph means two of them belong in `detail`. And if the metric cannot '
                'be made to explain itself in a few words, it is the wrong metric for this '
                'card -- change the metric rather than writing more prose around it.'
                % (id, name, len(text.strip()), cap))
    if not isinstance(figures, dict):
        raise ConclusionError('%s: figures must be a dict of name -> figure()' % id)
    for k, v in figures.items():
        if not (isinstance(v, dict) and set(v) == {'value', 'text', 'unit'}):
            raise ConclusionError('%s: figures[%r] was not built by figure()' % (id, k))
    # A CONCLUSION WITHOUT A NUMBER IS PROBABLY AN OBSERVATION. Two shipped here with an
    # empty headline and both had a strong figure sitting in their own payload; on a page
    # of stat boxes they read as an omission rather than a choice. So a headline is
    # required, and the one legitimate exception -- a conclusion whose whole point is that
    # NO published figure exists -- is stated rather than left as a blank, so
    # absence-by-design cannot be mistaken for absence-by-oversight.
    if figure is None and not no_figure:
        raise ConclusionError(
            '%s: no headline figure. A conclusion with no number is usually an '
            'observation that has not become a claim yet -- find the figure that makes it '
            'one, or drop it. If the POINT is that no published figure exists, say so in '
            'no_figure=.' % id)
    if figure is not None and no_figure:
        raise ConclusionError('%s: it cannot both have a headline figure and be about '
                              'there not being one' % id)
    if figure is not None:
        if figure not in figures:
            raise ConclusionError('%s: headline figure %r is not one of its figures'
                                  % (id, figure))
        # A UNIT-LESS HEADLINE IS IMPOSSIBLE TO PUBLISH, rather than merely absent today.
        # A number set large with its meaning three lines below in grey is a quantity
        # nobody can carry out of the room correctly.
        head = figures[figure]
        if not head['unit'] and not any(c in head['text'] for c in SELF_EVIDENT):
            raise ConclusionError(
                '%s: the headline figure %r renders as %r, which says nothing about what '
                'it counts. Give figure() a `unit` -- "children", "budget lines", "years" '
                "-- or, if the number needs a sentence to be intelligible, it is the "
                'wrong headline for this conclusion and another figure should carry it.'
                % (id, figure, head['text']))

    row = dict(id=id, claim=claim.strip(), so_what=so_what.strip(), detail=detail.strip(),
               figures=figures, kind=kind, bearing=bearing, basis=basis.strip(),
               not_shown=not_shown.strip(),
               see=[dict(slug=s, label=l) for s, l in (see or [])])
    if figure is not None:
        row['figure'] = figure
    if no_figure:
        row['no_figure'] = no_figure.strip()
    # SHIPPED, not stripped. These are the strings in the prose that are statutory names
    # or account codes rather than derived figures, and publishing them is what lets
    # verify_conclusions.py re-run this same check against the payload a reader gets
    # instead of against the generator's own working copy.
    row['literals'] = list(allow)
    return row


def check(report, rows):
    """Rule 2 as an assertion: no figure in a conclusion that nothing computed.

    Returns a list of problems. The caller raises; this returns, so a generator can print
    all of them at once rather than one per run.

    THE CHECK. Take the claim and the detail, remove every registered rendering and every
    declared literal, and look for a digit. One left standing is a number that was typed,
    which is the defect this whole project's rule 2 exists for -- three figures once
    shipped here stating amounts the model no longer produced, one off by $313,000.
    """
    bad, seen = [], set()
    for c in rows:
        cid = '%s/%s' % (report, c['id'])
        if c['id'] in seen:
            bad.append('%s: two conclusions share this id' % cid)
        seen.add(c['id'])

        prose = ' '.join((c['claim'], c.get('so_what', ''), c['detail']))
        for name, f in sorted(c['figures'].items()):
            if f['text'] not in prose:
                bad.append('%s: figure %r renders as %r and that string appears in none '
                           'of the claim, the supporting line or the detail'
                           % (cid, name, f['text']))
        residue = prose
        # Longest first, so a registered "$1,234,567" is taken before "$1,234".
        for t in sorted([f['text'] for f in c['figures'].values()]
                        + list(c.get('literals') or c.get('_allow') or ()),
                        key=len, reverse=True):
            residue = residue.replace(t, ' ')
        leftover = sorted(set(re.findall(r'\d[\d,.]*', residue)))
        if leftover:
            bad.append(
                '%s: %s appear in the prose and are not registered figures. Register each '
                'with figure(), or declare a statutory name in allow=().'
                % (cid, ', '.join(repr(x) for x in leftover)))
        if not c['figures'] and DIGIT_RE.search(residue):
            bad.append('%s: states a figure and registers none' % cid)
    return bad


def emit(report, rows):
    """Validate, and hand back the rows ready to go into a payload.

    Nothing is stripped: `literals` ships so the same check can be re-run against the
    published file rather than only against the generator's own copy of it.
    """
    problems = check(report, rows)
    if problems:
        raise ConclusionError(
            'conclusions for %s did not pass:\n  %s' % (report, '\n  '.join(problems)))
    return list(rows)


# ---- one voice for every figure in every conclusion -------------------------------
#
# The master report sets conclusions from sixteen generators side by side, and a reader
# takes a difference in FORMATTING for a difference in confidence -- the same reasoning
# that made components/report.tsx one shell rather than twenty. `$1.2M` beside
# `$1,234,567` beside `1234567` reads as three kinds of number. These are the renderings,
# and they live here so no generator has to invent one.

def usd(n):
    """A whole-dollar amount. Never abbreviated: a resident quoting `$2.1M` at a meeting
    cannot be challenged on it, and `$2,061,438` can be looked up."""
    n = round(float(n))
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',d')


def pct(x, dp=1):
    return '%.*f%%' % (dp, float(x))


def points(x, dp=1):
    """A change in a percentage, said as points. A percentage that moved from 8% to 10%
    did not rise 2% -- it rose 2 points, or 25%, and the two get confused constantly."""
    return '%.*f points' % (dp, float(x))


def num(n):
    return format(int(round(float(n))), ',d')


def fy(y):
    return 'FY%d' % int(y)


def fyspan(a, b):
    return 'FY%d to FY%d' % (int(a), int(b))


# ---- what a conclusion is ABOUT -----------------------------------------------------
#
# WHY A SECOND GROUPING EXISTS, AND WHY IT IS NOT A DUPLICATE OF THE FIRST.
#
# `/reports` groups the same reports by school / town / method, declared as `CATEGORIES`
# in scripts/build_reports_index.py. That grouping is right for an INDEX: a reader
# navigating asks "is this about the schools or the town", and the answer files every
# report exactly once.
#
# It is the wrong shape for CONCLUSIONS, and two cases show why. Special education is four
# reports, all filed under "what the money buys" because the index draws them behind one
# door -- but on a page of findings it is unarguably its own subject, and it is the subject
# this town argues about most. Athletics is two reports that the index separates, one under
# what the money buys and one under the students, because one is a cost and the other is a
# fee -- and a reader who wants to know what sport costs a household wants both together.
#
# So the two groupings differ on purpose. This is the ONLY declaration of the second one;
# `build_reports_index.py` reads it and REFUSES TO WRITE if a report it lists is in neither
# taxonomy, so a report added to the site cannot fall silently out of one of them.
#
# Kept to five, deliberately. The whole value of the synthesis page is that a reader can
# take in the shape of everything at once, and eight sections of two conclusions each is a
# list wearing headings.
TOPICS = [
    ('sped', 'Special education',
     'The subject this town argues about most, in reports that do not combine: how many '
     'children, what it costs, where a placement leads, and the state rule the whole '
     'argument runs under.',
     ['spedcount', 'spedcost', 'spedroute', 'classsize']),
    ('income', 'Where the school money comes from',
     'State aid, the minimum the state requires, what other districts spend, and what '
     'happened when the grants ended.',
     ['minaid', 'formula', 'required', 'peers', 'unwind']),
    ('spending', 'What the money buys, and what it does not',
     'Staffing, the classes that ran, insurance, the lines that stopped, what the '
     'district said it was cutting, and how close the budget lands to what gets spent.',
     ['staffing', 'schoolstaff', 'parastaff', 'courses', 'insurance', 'stopped',
      'cuts', 'variance']),
    ('children', 'Where the children are',
     'Which grades they leave in, who is taught outside Lunenburg, what the town is '
     'assessed for them, and what more leaving would cost.',
     ['enrollment', 'attrition', 'outflow', 'montytech', 'leaving']),
    # THE HOUSEHOLD, and it is broader than it was. It held the two reports about money a
    # family hands over; it now opens with the report about who those households ARE.
    # `bythenumbers` belongs here rather than in a sixth topic: the ACS's own grain is the
    # HOUSEHOLD -- 4,529 of them, a third with a child under 18, four in five owning their
    # home -- and a reader who wants to know what a family pays wants to know how many
    # families there are and what they earn. The five-topic cap holds, deliberately: the
    # value of the synthesis page is that the shape of everything fits in one view.
    ('household', 'The households — who they are, and what they pay',
     'Who lives in Lunenburg, and the two reports about money a household hands over, '
     'side by side.',
     ['bythenumbers', 'sportsmoney', 'families']),
]

# Tabs in the Analyses area that are not reports and belong in no topic: the Markdown
# renderer, the four-way chooser at /special-education, and the synthesis page itself.
# `blog` is the fourth and it is the same kind of thing as `addsup` from the other end: it
# reaches no conclusion of its own, it re-presents what the reports already concluded, and
# a topic heading over it would file the whole archive under one subject.
# `recorded` and `thisweek` are announcements and finding aids, not analyses with
# conclusions to synthesise.
NOT_A_REPORT = ('analysis', 'sped', 'addsup', 'blog', 'recorded', 'thisweek')


def topic_of(tab):
    for key, _title, _blurb, tabs in TOPICS:
        if tab in tabs:
            return key
    return None
