#!/usr/bin/env python3
"""How Chapter 70 actually works, in eight steps, without the jargon.

    python3 scripts/build_ch70_formula.py
    python3 scripts/build_ch70_formula.py --check

WHY THIS IS A PAGE AND NOT A SECTION OF /why-we-only-get-minimum-aid.

That page establishes Lunenburg's POSITION: the whole FY2026 increase is the Legislature's
flat floor, the town sits $249,645 above the line at which the formula pays anything, and
its required contribution is a wealth calculation with no pupil count in it. It answers
"where are we".

This page answers "how does the thing WORK". The two are different questions and a reader
arriving with the second one should not have to read twenty years of aid components to get
it. TJ was explicit that it is its own page.

THE EIGHT STEPS ARE THE ARTEFACT, AND THEY ARE NOT AUTHORED HERE.

`HOW_IT_WORKS` lives in scripts/build_minimum_aid.py, where it was written, and its own
comment records why the ORDER matters: every step answers the question the previous one
raises. TJ, after an hour of questions: "we absolutely need to document this and explain it
this way without the jargon. this is very clear and the first time i truly get it!"

So this generator IMPORTS them and publishes them unchanged. It does not reorder them, does
not compress them and does not paraphrase them, and `verify_ch70_formula.py` asserts the
published list is identical -- same order, same wording -- to the one in that module. A
page that rewrote the sequence would have destroyed the only thing on it that took an hour
to find.

THE UNLOCK, WHICH IS STEP 4: Chapter 70 is not recalculated from your students each year.
It is last year's aid plus an increment, and the increment can be zero. Every confusing
thing about Lunenburg's aid follows from that one fact.

WHY IT IMPORTS THE OTHER GENERATOR'S `build()` RATHER THAN READING ITS PUBLISHED FILE.

The two pages share figures -- the foundation budget, the required contribution, the
per-pupil floor -- and the brief is that they must not be able to disagree. Reading
`minimum-aid.json` off disk would make this page's figures as fresh as the last time
somebody ran that generator; calling `build()` makes them the same computation, in the same
process, off the same database rows. There is no version of this in which the two differ.

WHAT IS ESTABLISHED HERE, AND IT IS ARITHMETIC ON PUBLISHED FIGURES.

  1. Three numbers that get confused, and two of them are the same figure for different
     reasons: $5,757.59 is the aid for each foundation pupil, $150.00 is this year's
     INCREASE per pupil, and $150.00 is also what one more pupil moves the aid by -- the
     last two coincide in FY2026 because minimum aid is the only component operating.
  2. DESE's own definitions name TWO provisions that reduce Chapter 70 aid. One is a
     legislated across-the-board percentage cut. The other applies only to NON-OPERATING
     districts, which run no schools. Lunenburg runs schools. Neither is enrolment.
  3. The workbook's reduction column is populated in FY2009, FY2010 and FY2011 -- the
     recession years. Step 8 names two of the three; the measured set is printed beside it
     rather than the step being edited, because the step is the artefact and the column is
     the evidence.

WHERE THE CLAIM STOPS, AND THE PAGE SAYS IT IN THESE WORDS.

"Fewer students does not mean less aid -- it means no increase" was established AT THE
MARGIN: one pupil, holding everything else at its FY2026 value. It is not a rate that
extrapolates. Below about 968 foundation pupils -- 60.4% of today's count -- the foundation
budget falls below the town's required contribution and step 3's subtraction turns
negative, and nothing in this archive models what the formula does there. It has not
happened in any of the twenty years DESE publishes here. Those figures are computed, not
typed; see `threshold` below and the `money_gaps` row this page cites rather than restates.
"""
import argparse
import json
import os
import sys

import conclusions as C
from conclusions import conclusion, emit, figure

import build_minimum_aid as MA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'ch70-formula.json')

# The report id, which is its address. `emit` keys the rule-2 check on it and
# /what-it-all-adds-up-to keys its own grouping on the TAB, so the two are deliberately
# different strings and neither is derived from the other.
REPORT = 'how-chapter-70-works'

# The eight steps, and nothing else, are what this page is for. A count kept here so that
# a step quietly added or dropped upstream stops this build rather than changing the page.
STEPS = 8

# The two DESE definitions that name a reduction, by CELL rather than by term -- a term can
# be reworded in a glossary and a cell cannot be renamed without the workbook changing.
REDUCTION_CELLS = ('User Guide!B41', 'User Guide!B42')

# The definitions the steps rest on, in the order the steps meet them. Rule 13: the page
# quotes DESE, and quoting is what separates "the formula works this way" from "our reading
# of the numbers suggests".
DEFINITION_CELLS = ('User Guide!B17', 'User Guide!B24', 'User Guide!B26',
                    'User Guide!B34', 'User Guide!B38',
                    'User Guide!B41', 'User Guide!B42', 'User Guide!B45')

# What the town said, out of the eight quotes the other generator re-reads from the
# extracted minutes on every run. Three, chosen for what they show about the MECHANISM
# rather than about Lunenburg's position: the rate being set, a description of the formula
# given to the Finance Committee, and the town asking the Legislature to reopen the two
# halves of it.
QUOTE_KEYS = ('passed', 'novick', 'commission')

# The limits this page hits, cited from the registry rather than restated (rule 7c).
WANTED_GAPS = [
    'What Chapter 70 aid would actually do if enrollment fell',
    'What the foundation budget pays per pupil for each kind of child',
    'How many children Chapter 70 is actually paid for',
]


def fail(msg):
    raise SystemExit('%s\nNothing written.' % msg)


def usd2(n):
    """A per-pupil rate, to the cent.

    `conclusions.usd` rounds to whole dollars, which is right everywhere else on this site
    and wrong here: the whole of this page is that $150.00 is EXACTLY the floor and
    $5,757.59 is a different quantity that happens to start with the same digit run. A
    rounded $5,758 beside step 6's own "about $5,757 a pupil" would read as two figures.
    """
    n = float(n)
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',.2f')


def build():
    m = MA.build()

    steps = MA.HOW_IT_WORKS
    if len(steps) != STEPS:
        fail('build_minimum_aid.HOW_IT_WORKS has %d steps and this page publishes %d. The '
             'sequence is the artefact; a step added or dropped is a decision about the '
             'explanation, not a build detail.' % (len(steps), STEPS))
    for i, s in enumerate(steps, 1):
        if not (s.get('step') and s.get('plain') and s.get('watch')):
            fail('step %d has no step, plain or watch. Every step carries all three, and '
                 'the `watch` line is where the misreadings actually happened.' % i)

    by_cell = {d['cell']: d for d in m['definitions']}
    missing = [c for c in DEFINITION_CELLS if c not in by_cell]
    if missing:
        fail('DESE definitions %s are no longer in the workbook extract. This page QUOTES '
             'them; a page that lost its quotations would go on rendering the steps as '
             'though nothing had changed.' % ', '.join(missing))
    definitions = [by_cell[c] for c in DEFINITION_CELLS]
    reductions = [by_cell[c] for c in REDUCTION_CELLS]

    h, z, mg = m['headline'], m['why_zero'], m['marginal']
    fy, enrol = h['fy'], h['enrollment']
    aid_per_pupil = h['aid'] / enrol
    floor_rate = h['per_pupil']
    if floor_rate <= 0:
        fail('the FY%d per-pupil increase is %r. Three of this page\'s four sections '
             'divide by it.' % (fy, floor_rate))

    # ---- THE THREE NUMBERS, and why two of them are the same -------------------------
    # The marginal figure is the floor rate BECAUSE minimum aid is the only component
    # operating: the formula's own aid term produced nothing, so the only part of the
    # build-up that responds to a pupil is the flat per-pupil increase. Asserted rather
    # than assumed -- if the formula ever pays foundation aid again the two stop being
    # the same number and the page's own sentence about the coincidence is wrong.
    if h['foundation_aid_increment'] != 0:
        fail('FY%d pays a foundation aid increment of %s. This page states that the '
             'per-pupil increase and the marginal effect of one pupil coincide BECAUSE '
             'minimum aid is the only component operating, and that has stopped being '
             'true.' % (fy, C.usd(h['foundation_aid_increment'])))

    three = [
        dict(key='aid_per_pupil', value=aid_per_pupil, text=usd2(aid_per_pupil),
             label='Chapter 70 aid, for each foundation pupil',
             what='What the state actually sends, divided by the pupils the formula counts. '
                  'The size of the aid.'),
        dict(key='increase_per_pupil', value=floor_rate, text=usd2(floor_rate),
             label='This year’s INCREASE, for each foundation pupil',
             what='The rate the Legislature set for %s. It is an increase over last year’s '
                  'aid, not the aid.' % C.fy(fy)),
        dict(key='marginal_per_pupil', value=floor_rate, text=usd2(floor_rate),
             label='What one more pupil moves the aid by',
             what='The same figure as the one above it, for a different reason: minimum aid '
                  'is the only component operating, so the only part of the build-up that '
                  'responds to a pupil is the flat per-pupil increase.'),
    ]
    ratio = aid_per_pupil / floor_rate

    # ---- THE THREE YEARS THE REDUCTION COLUMN IS POPULATED ---------------------------
    # Step 8 names FY2010 and FY2011. The workbook's column is populated in three years,
    # and the measured set is printed beside the step rather than the step being edited:
    # the step is the artefact, the column is the evidence, and step 8's claim is about
    # WHAT KIND of rule a reduction is, not about which years it ran in.
    cut_years = [dict(fy=s['fy'], amount=s['reduction'])
                 for s in m['series'] if s['reduction']]
    if not cut_years:
        fail('no year in the series carries a reduction. The page states that an '
             'across-the-board cut is one of the two things that can reduce aid and shows '
             'the years it happened; a join that matched nothing looks exactly like a '
             'state that never cut.')

    # ---- WHERE THE MARGINAL CLAIM STOPS ----------------------------------------------
    # Foundation budget scales with pupils; the required contribution does not, because it
    # is the combined effort yield path. So step 3's subtraction -- foundation budget less
    # required contribution -- turns negative below the pupil count at which the two are
    # equal. That is a THRESHOLD in the arithmetic, not a prediction about what the
    # Legislature would do, and the page says so in those words.
    share_now = z['required_local_contribution'] / z['foundation_budget']
    pupils_at_zero = enrol * share_now
    ever_negative = [s['fy'] for s in m['series']
                     if s['foundation_budget'] < s['required_local_contribution']]
    if ever_negative:
        fail('the foundation budget is below the required contribution in %s. The page '
             'states that it has not happened in any published year.'
             % ', '.join('FY%d' % f for f in ever_negative))
    threshold = {
        'fy': fy,
        'enrollment': enrol,
        'required_share': share_now,
        'pupils_at_zero': pupils_at_zero,
        'fall_pct': 1 - share_now,
        'years_checked': m['years'],
        'first_fy': m['fy_first'], 'last_fy': m['fy_last'],
        'highest_share': max(s['required_share'] for s in m['series']),
        'highest_share_fy': max(m['series'], key=lambda s: s['required_share'])['fy'],
        'is_measurement': False,
        'assumptions': mg['assumptions'],
    }

    said = []
    for k in QUOTE_KEYS:
        hit = [q for q in m['said'] if q['key'] == k]
        if not hit:
            fail('the quote keyed %r is no longer in the minutes extract. Rule 13: quote '
                 'the source, never your rendering of it.' % k)
        said.append(hit[0])

    gaps = []
    for want in WANTED_GAPS:
        hit = [g for g in m['gaps'] if g['what'].startswith(want)]
        if not hit:
            fail('money_gaps has no row beginning %r. Rule 7c: the registry outranks the '
                 'page, so a rename there stops this build rather than silently dropping '
                 'a limit.' % want)
        gaps.append(hit[0])

    # ---- THE CONCLUSIONS -------------------------------------------------------------
    #
    # BEARING IS `sizes` FOR ALL FOUR, and the argument is worth writing down because
    # `lever` is tempting here. This page reframes three live arguments in town -- that
    # falling enrolment is costing the town aid, that new housing would bring aid, that
    # school choice drains it -- which FEELS like a lever. It is not one. `lever` means a
    # body in this town can decide the thing, and every quantity on this page is set
    # somewhere else: the per-pupil rates are DESE's, the floor is a line in the
    # Legislature's budget, the required contribution is a wealth calculation, and the
    # sequence itself is statute. Nothing here is a dial anybody in Lunenburg turns. What
    # the page does is stop a town spending its argument on a number that cannot move --
    # which is sizing, and it is the most useful sizing on the site.
    conclusions = emit(REPORT, [
        conclusion(
            id='fewer-students-does-not-mean-less-aid',
            claim='What one more or one fewer foundation pupil moves Lunenburg’s state aid by',
            so_what='Losing pupils does not cut the aid. It changes only the flat increase, which is set on Beacon Hill.',
            lede='Chapter 70 is not recalculated from your students each year. It is last '
                 'year’s aid plus an increase, and in %s the only increase available was '
                 'the Legislature’s flat floor — %s a pupil. So one pupil more or fewer '
                 'moves the aid by that, and by nothing else.'
                 % (C.fy(fy), usd2(floor_rate)),
            detail='DESE’s own rule is a floor test rather than a recalculation: “If '
                   'foundation aid is greater than prior year Chapter 70 aid, the district '
                   'receives a foundation aid increase.” Only greater. Lunenburg already '
                   'receives more than the formula says it needs, so that term paid %s in '
                   '%s and the whole increase was the flat rate. A pupil changes the '
                   'foundation budget, which is an input to a term producing nothing — and '
                   'it changes the town’s required contribution not at all, because that is '
                   'worked out from property values and income. Measured one pupil at a '
                   'time, holding everything else at its %s value.'
                   % (C.usd(h['foundation_aid_increment']), C.fy(fy), C.fy(fy)),
            figures=dict(
                fy=figure(fy, C.fy(fy)),
                marginal=figure(floor_rate, usd2(floor_rate), unit='per pupil'),
                foundation_aid=figure(h['foundation_aid_increment'],
                                      C.usd(h['foundation_aid_increment']))),
            figure='marginal',
            kind='measured',
            bearing='sizes',
            allow=('Chapter 70',),
            basis='DESE’s Chapter 70 Trends workbook, sheets %s and %s, and DESE’s own '
                  'definition of the foundation aid increase at %s. The %s aid components '
                  'as DESE ran them, with the town’s required contribution held fixed '
                  'because DESE’s target local contribution equals the combined effort '
                  'yield in every published year.'
                  % (MA.SHEET_AID, MA.SHEET_CONTRIB, 'the workbook’s User Guide', C.fy(fy)),
            not_shown='What a large loss of pupils would do. This is a marginal rate and it '
                      'does not extrapolate: below the point where the foundation budget '
                      'falls under the required contribution the formula’s own subtraction '
                      'turns negative, and no document here models that. Nor is aid the '
                      'whole cost of a departing pupil — a school choice transfer also '
                      'takes a tuition payment with it.',
            see=[('/why-we-only-get-minimum-aid',
                  'why Lunenburg is on the floor in the first place'),
                 ('/if-students-leave', 'what a departing pupil costs, tuition included')],
        ),
        conclusion(
            id='the-aid-and-the-increase-are-different-numbers',
            claim='Chapter 70 aid for each foundation pupil in %s, against %s of increase'
                  % (C.fy(fy), usd2(floor_rate)),
            so_what='The figure everybody quotes is an increase, not the aid. They differ by a factor of %s.'
                    % C.num(ratio),
            lede='Three numbers get used interchangeably in this town and two of them are '
                 'the same figure for different reasons. Chapter 70 pays %s for each of '
                 'the %s pupils the formula counts. This year’s increase is %s a pupil. '
                 'And one more pupil moves the aid by %s.'
                 % (usd2(aid_per_pupil), C.num(enrol), usd2(floor_rate), usd2(floor_rate)),
            detail='The last two coincide in %s, and only because minimum aid is the sole '
                   'component operating — the formula’s own aid term paid nothing, so the '
                   'flat per-pupil increase is the only part of the build-up a pupil can '
                   'move. They are not the same quantity and in a year when the formula '
                   'pays they will not be the same number. The first is a different kind of '
                   'figure again: it is the aid divided by the pupils, and quoting it '
                   'beside the other two is how a town comes to believe that a pupil is '
                   'worth %s of state money.'
                   % (C.fy(fy), usd2(aid_per_pupil)),
            figures=dict(
                fy=figure(fy, C.fy(fy)),
                aid_per_pupil=figure(aid_per_pupil, usd2(aid_per_pupil),
                                     unit='aid per pupil'),
                increase=figure(floor_rate, usd2(floor_rate)),
                enrollment=figure(enrol, C.num(enrol)),
                ratio=figure(ratio, C.num(ratio))),
            figure='aid_per_pupil',
            kind='measured',
            bearing='sizes',
            allow=('Chapter 70',),
            basis='DESE’s `%s` sheet: Chapter 70 aid and foundation enrollment for '
                  'Lunenburg Public Schools in %s, and the minimum aid increment in the '
                  'same row.' % (MA.SHEET_AID, C.fy(fy)),
            not_shown='What the state pays for any particular child. The foundation budget '
                      'is built from rates that differ by grade and by category, and an '
                      'average across all of them is not the amount attached to any pupil.',
            see=[('/what-other-districts-spend', 'what a pupil costs, against every district')],
        ),
        conclusion(
            id='nothing-in-the-formula-takes-aid-away-for-losing-pupils',
            claim='Provisions in DESE’s own definitions that can reduce a district’s Chapter 70 aid',
            so_what='One is a legislated across-the-board cut. The other applies only to districts that run no schools.',
            lede='DESE’s glossary names %s things that reduce Chapter 70 aid, and neither '
                 'of them is enrolment for a district that runs its own schools.'
                 % C.num(len(reductions)),
            detail='The first decreases aid by a fixed percentage, legislated and applied to '
                   'everybody — the workbook’s reduction column is populated for Lunenburg '
                   'in %s, the recession years, and in no year since. The second reduces '
                   'aid to the level of the foundation budget for NON-OPERATING districts, '
                   'which run no schools of their own and tuition their pupils elsewhere. '
                   'Lunenburg runs schools. There is no provision that cuts an operating '
                   'district’s aid because it has fewer children: what falling enrolment '
                   'reaches is the increase, not the base.'
                   % MA.and_list(['%s (%s)' % (C.fy(c['fy']), C.usd(c['amount']))
                                 for c in cut_years]),
            figures=dict(
                provisions=figure(len(reductions), C.num(len(reductions)),
                                  unit='provisions that reduce aid'),
                **{('cut_%d' % c['fy']): figure(c['amount'], C.usd(c['amount']))
                   for c in cut_years},
                **{('cut_fy_%d' % c['fy']): figure(c['fy'], C.fy(c['fy']))
                   for c in cut_years}),
            figure='provisions',
            kind='measured',
            bearing='sizes',
            allow=('Chapter 70',),
            basis='DESE’s own definitions in the workbook’s User Guide, quoted at their '
                  'cells, and the reduction column of the `%s` sheet for Lunenburg across '
                  '%s.' % (MA.SHEET_AID, C.fyspan(m['fy_first'], m['fy_last'])),
            not_shown='That these are the only provisions in statute. The User Guide is '
                      'DESE’s glossary for its own workbook, not Chapter 70 itself, and a '
                      'component absent from the glossary would be absent from this page '
                      'too. Nor does any of it say what a future Legislature will do.',
            see=[('/why-we-only-get-minimum-aid',
                  'the aid components, term by term, for twenty years')],
        ),
        conclusion(
            id='the-marginal-rate-does-not-extrapolate',
            claim='Foundation pupils at which the formula’s own subtraction would turn negative',
            so_what='%s below today. The per-pupil finding was measured at the margin and stops well above it.'
                    % C.pct(100 * threshold['fall_pct']),
            lede='Everything on this page about one more or one fewer pupil was measured '
                 'AT THE MARGIN. It is not a rate that can be multiplied out: below about '
                 '%s foundation pupils the town’s foundation budget falls under its '
                 'required contribution and step 3 of the formula turns negative.'
                 % C.num(pupils_at_zero),
            detail='The required contribution is a wealth calculation and does not move '
                   'with pupils; the foundation budget does. In %s the required '
                   'contribution is %s of the foundation budget, so the two would meet at '
                   'roughly %s of today’s %s pupils. Nothing in this archive models what '
                   'the formula does from there, and it has not happened in any of the %s '
                   'years DESE publishes here — the highest the required share has been is '
                   '%s, in %s. What this page establishes is the behaviour of the formula '
                   'near where Lunenburg actually sits.'
                   % (C.fy(fy), C.pct(100 * share_now), C.pct(100 * share_now),
                      C.num(enrol), C.num(m['years']),
                      C.pct(100 * threshold['highest_share']),
                      C.fy(threshold['highest_share_fy'])),
            figures=dict(
                pupils=figure(pupils_at_zero, C.num(pupils_at_zero), unit='foundation pupils'),
                fall=figure(100 * threshold['fall_pct'], C.pct(100 * threshold['fall_pct'])),
                fy=figure(fy, C.fy(fy)),
                share=figure(100 * share_now, C.pct(100 * share_now)),
                enrollment=figure(enrol, C.num(enrol)),
                years=figure(m['years'], C.num(m['years'])),
                highest=figure(100 * threshold['highest_share'],
                               C.pct(100 * threshold['highest_share'])),
                highest_fy=figure(threshold['highest_share_fy'],
                                  C.fy(threshold['highest_share_fy']))),
            figure='pupils',
            kind='measured',
            bearing='sizes',
            # `step 3` is a POSITION in the eight-step sequence this page publishes, not a
            # derived figure. Declared rather than reworded: the steps are numbered on the
            # page and pointing at one by its number is how a reader follows the argument.
            allow=('Chapter 70', 'step 3'),
            basis='The %s foundation budget and required local contribution from DESE’s '
                  '`%s` sheet, with the foundation budget scaled by pupils at its own '
                  'average and the required contribution held fixed — which is DESE’s own '
                  'structure, not an assumption: the target local contribution equals the '
                  'combined effort yield in every published year and carries no pupil '
                  'term.' % (C.fy(fy), MA.SHEET_AID),
            not_shown='What the formula would actually pay at that enrollment. This is the '
                      'point at which one subtraction in the sequence changes sign, not a '
                      'projection: a district that far off its foundation budget would meet '
                      'hold-harmless provisions, a different minimum aid rate and possibly '
                      'legislation, none of which is in this workbook.',
            see=[('/what-we-cannot-answer', 'the limits, as the registry records them')],
        ),
    ])

    return {
        'conclusions': conclusions,
        'about': 'Chapter 70 explained in eight plain steps, in the order the questions '
                 'actually arrive — what the state prices, what it decides the town can '
                 'afford, and the one fact everything else follows from: aid is last '
                 'year’s aid plus an increase, and the increase can be zero.',
        'not_this_page': 'Lunenburg’s position. Where the town sits in this formula, the '
                         'twenty-year series of aid components, the peer districts on the '
                         'same per-pupil rate and the wealth calculation behind the '
                         'required contribution are on /why-we-only-get-minimum-aid. This '
                         'page is the mechanism, with %s used to show it working.'
                         % C.fy(fy),
        'source': m['source'],
        'fy': fy,
        'fy_first': m['fy_first'], 'fy_last': m['fy_last'], 'years': m['years'],
        'how_it_works': steps,
        'unlock': steps[3]['step'],
        'three_numbers': three,
        'ratio': ratio,
        'aid': h['aid'],
        'enrollment': enrol,
        'increase': h['increase'],
        'foundation_aid_increment': h['foundation_aid_increment'],
        'foundation_budget': z['foundation_budget'],
        'required_local_contribution': z['required_local_contribution'],
        'need': z['need'], 'prior_aid': z['prior_aid'], 'headroom': z['headroom'],
        'foundation_per_pupil': h['foundation_per_pupil'],
        'definitions': definitions,
        'reductions': reductions,
        'cut_years': cut_years,
        'threshold': threshold,
        'said': said,
        'searched': m['searched'],
        'minutes': m['minutes'],
        'gaps': gaps,
        'not_established': [
            'What a large fall in enrollment would do to the aid. The finding on this page '
            'is a marginal one — one pupil, everything else held at its FY%d value — and a '
            'marginal rate multiplied out is not a projection.' % fy,
            'What the state pays for any particular child. The foundation budget is built '
            'from rates that differ by grade and by category, and the workbook publishes '
            'Lunenburg’s categories without the rates, so the average of $%s a pupil is '
            'not the amount attached to anybody.'
            % format(round(h['foundation_per_pupil']), ','),
            'That the Legislature sets the same floor next year. Minimum aid is voted each '
            'year, it was not available at all in some years, and DESE’s own definition '
            'says so: “Not available in every year.”',
            'Whether these are the only provisions in statute that reduce aid. The two on '
            'this page are the two DESE’s glossary for its own workbook names.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_ch70_formula.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    t = data['threshold']
    print('%s: %d steps, FY%d' % (os.path.relpath(OUT, ROOT), len(data['how_it_works']),
                                  data['fy']))
    for n in data['three_numbers']:
        print('  %-14s %s  %s' % (n['key'], n['text'], n['label']))
    print('  reduction provisions in DESE’s glossary: %d; column populated in %s'
          % (len(data['reductions']),
             ', '.join('FY%d' % c['fy'] for c in data['cut_years'])))
    print('  step 3 turns negative below %s pupils — a fall of %.1f%% from %s — and has '
          'not in %d published years'
          % (format(round(t['pupils_at_zero']), ','), 100 * t['fall_pct'],
             format(round(t['enrollment']), ','), t['years_checked']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
