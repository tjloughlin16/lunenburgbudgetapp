#!/usr/bin/env python3
"""What a Lunenburg family actually pays the schools in a year — and why it is a floor.

    python3 scripts/build_what_families_pay.py            # write it
    python3 scripts/build_what_families_pay.py --check    # fail if it is stale

WHERE THIS CAME FROM. Two things residents say at meetings, put to this site as a
question. One: parents should pay more, because they are the ones using the schools.
Two: parents — athletes' families especially — already pay a great deal. Both are claims
about a number, so the obvious move is to compute the number for families of one, two,
three and four children.

THE ANSWER IS NOT A NUMBER, AND THAT IS THE PAGE. Three separate things stop it:

  1. THE FAMILY CAP HAS NO STATED PERIOD. The School Committee set it on 26 February 2025
     and the minutes say only "with a family cap of $1500". The cap it replaced DID state
     one — the LHS Athletics FAQ prints "Total Cap per season=$475.00". Read per season and
     read per year, the same two words are a different bill for the same family.
  2. SIX FEES THE DISTRICT SELLS HAVE NO PUBLISHED AMOUNT. They are in `rate_register` with
     `status='not_published'`, established as existing and not as costing anything. So
     every total here is a FLOOR with a band above it that has no top, and the band is
     reported as a COUNT OF NAMED FEES rather than as a dollar estimate. Rule 7: we do not
     have the amounts, so we do not publish a guess at them.
  3. THERE IS NO PUBLISHED RATE FOR A FOURTH CHILD in FY2027. First, second and third are
     named and the ladder stops — and a family of four is exactly what the question asked
     about. The rule is nevertheless VISIBLE: 400 x 0.75 is exactly 300 and 400 x 0.75^2 is
     exactly 225, so the 25% sibling discount the committee voted is compounding down the
     ladder. The fourth child at $168.75 and the fifth at $126.56 follow from that ratio,
     and this page labels every rung produced that way as inferred rather than published.
     It is unpublished, not unknowable, and those are different words.

WHAT THE ARITHMETIC DOES ESTABLISH, AND WHERE THE INFERENCE STARTS (rule 7, and this is
the section that most needs the line drawn on it):

  MEASURED. With the FY2027 ladder as published — 400, 300, 225 — three children each
  playing one sport in one season come to $925. The cap is $1,500. It does not bind. Carry
  the ladder out and FIVE children at one sport each in one season still do not reach it,
  on either available assumption: $1,220 if the 25% keeps compounding, $1,375 if the
  discount stops descending and the fourth and fifth pay the third-child rate. The page
  computes both, because the conclusion has to survive the choice between them.
  Under a per-year reading the same cap binds at three children and two sports each.

  MEASURED, AND THE OTHER HALF OF THE ARGUMENT. A qualifying family pays a flat reduced
  fee with no ladder — $50 a season a child at the high school in FY2026 — so three
  athletes cost that family $150 a season against $925 at the full rate. "Parents" is not
  one group and this page prices all three tiers rather than the loudest one.

  MEASURED, ABOUT PERIODS. The town states a period when it means one. The Finance
  Committee minutes of 20 March 2025 describe the BUS fee, set in the same budget cycle,
  as "$180 and the family cap is $270 for the year". For athletics, four weeks earlier, it
  did not.

  INFERRED, and labelled as an inference everywhere it appears: a cap that no ordinary
  family can reach is not doing the work a cap does, so the arithmetic makes a per-season
  reading implausible. NOTHING PUBLISHED STATES THE PERIOD. That inference is an argument
  a resident can follow with no data at all, which is why it leads — and it is not a
  measurement, which is why the page says so in the same breath and registers the gap.

  AND THE FY24/FY25 IDENTITY IS THE REASON THE INFERENCE HAS TEETH. Under the old schedule
  the three published rates sum to EXACTLY the printed cap: 250 + 140 + 85 = 475. A cap set
  at the sum of the ladder is a cap that binds the moment a fourth child appears. The FY2027
  cap sits $575 above the same sum, so whatever it is doing, it is not doing that.
  `extract_fee_schedule.py` asserts the FY25 identity and refuses to write without it.

RULE 6, AND A GROWTH RATE THAT IS NOT COMPUTED HERE. $475 and $1,500 are NOT a like-for-
like rise. One is stated per season, the other states no period, and one is a high school
cap while the other is recorded against `ANY`. No rate of change is computed across them
and none may be.

RULE 8. The fees are set in public, by roll call, and the schedule is on the district's own
site. Nothing here says anybody set a wrong fee. What the page says is that the archive
cannot pin the cap's period and that six fees carry no published amount, and both of those
close on one document that one email would produce.

RULE 11 SITS UNDER ALL OF IT. A fee is money in. The budget lines these fees offset are
NET of them, which is why "what a family pays" and "what the town is spared" are different
questions and this page answers only the first.

WHAT IT REFUSES TO WRITE ON. Nine joins or assertions that could silently match nothing:
  1. the athletic fee schedule missing any rate this page prices a scenario from;
  2. a rate whose `unit_status` is not one of the three the page renders;
  3. the FY25 ladder no longer summing to the FY25 printed cap;
  4. the FY26 or FY27 cap having acquired a stated period without this page noticing;
  5. `rate_register` no longer carrying the bus fees, or carrying a different tier set;
  6. fewer than two fees with `status='not_published'` — the unknown band's whole basis;
  7. the FY2027 ladder no longer being the FY2026 sibling discount compounding, which is
     what makes the unpublished rungs inferable rather than unknowable;
  8. a meeting quote no longer present verbatim in the file it is attributed to;
  9. a `money_gaps` row quoted by key having been renamed out from under the page.
"""
import argparse
import json
import os
import re
import sqlite3
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py: the generator that computed a figure writes the claim that rests
# on it, and `emit()` refuses to ship a figure nothing computed.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/what-families-pay.json')
REPORTS = os.path.join(ROOT, 'fy28/public/data/reports.json')
MINUTES = 'sources/meetings/text'
FAQ_REL = 'sources/district-budget/text/lhs-athletics-faq.txt'
# The only sentence in the archive establishing that a fee can be waived to zero. It is
# in the FAQ, which states no year, so it is quoted as the basis of the tier and not as
# an FY2027 rate -- the same undated-schedule trap that cost this project 31% of modelled
# fee revenue once already.
FAQ_WAIVER = ('LHS Athletics FAQ: "Students that are on the free lunch program have the '
              'athletic fee waived". The FAQ states no year.')

# The years a reader can price. FY2027 is the year now running and the one the question was
# asked about; FY2026 is the last year with a schedule published in full, and the contrast
# between the two is itself a finding — FY2026 publishes a middle school rate, a reduced
# rate and a sibling discount, and FY2027 publishes none of the three.
YEARS = [2027, 2026]
# The years whose cap the page compares periods on. FY2025 is the stated-period predecessor.
CAP_YEARS = [2025, 2026, 2027]
SEASONS = 3          # Fall, Winter, Spring — the workbook's own three worksheets
MAX_CHILDREN = 4     # the question as it was asked
MAX_SPORTS = 3       # one sport per season, and there are three seasons
LADDER_CHILDREN = 5  # the exhibit that carries the ladder past what is published

# The bus tiers, by fiscal year, as `rate_register` records them. Named rather than
# discovered so a tier disappearing is a failure and not a smaller table.
BUS_ITEMS = ['one student', 'one student, reduced', 'two or more students',
             'two or more, reduced', 'qualifying families']

# WHAT THE TOWN SAID. Rule 15a: found with scripts/search_minutes.py, and each asserted
# below to still be present verbatim in the document it is attributed to.
QUOTES = [
    dict(key='thevote',
         board='school-committee', date='2025-02-26', doc='7076', kind='minutes',
         quote='A slideshow presentation of athletic user fees is presented to increase fee '
               'for high school up to $325 and $275 for Middle School.  A 25% discount for '
               'siblings.  Reduced fee for high school to $50 and $40 for middle school '
               'with a family cap of $1500.',
         who='School Committee, moved and approved by roll call',
         why='The whole of what any document in this archive says about the family cap. '
             'It is one sentence, it names an amount, and it names no period. Everything '
             'on this page about the cap runs off this sentence and the one it replaced.'),
    dict(key='fourfifty',
         board='school-committee', date='2025-02-26', doc='7076', kind='minutes',
         quote='As far as the student activities is concerned, when I looked at the list, I '
               'personally participate in 6 of them.  That would cost $450 which is more '
               'than any of the athletic fees were raised.',
         who='Kara Harunkiewicz, in public comment at the same meeting',
         why='Said in the room where the athletic fees were voted, and it is the point '
             'this page is built to test: athletics is the fee everybody argues about and '
             'it is not the only one a family pays. '
             'IMPORTANT, AND THIS CORRECTS AN EARLIER VERSION OF THIS PAGE: the $450 is '
             'this resident’s arithmetic on the fee structure PROPOSED that night — a base '
             'fee with a further fee per activity — and that structure is not what the '
             'committee adopted. On 7 May 2025 it took a single universal rate instead, '
             'quoted below. Under what was actually voted, joining six activities costs '
             'what joining one costs. The earlier version of this page recorded the '
             'activity fee as discussed and never voted, which was wrong: it was voted, '
             'the minute is in this archive, and the fee has been charged since.'),
    dict(key='fortheyear',
         board='finance-committee', date='2025-03-20', doc='7010', kind='minutes',
         quote='The fee for 1 child is $180 and the family cap is $270 for the year.',
         who='the Finance Committee, on the bus fee set eight days earlier',
         why='The same district, the same budget cycle, a family cap — and the period '
             'stated in so many words. Four weeks before this, the athletic cap was voted '
             'with no period at all. That does not establish what the athletic cap means. '
             'It does establish that stating the period is something the town does when it '
             'has one in mind, so the omission is not a convention of minute-taking.'),
    dict(key='activityvote',
         board='school-committee', date='2025-05-07', doc='7207', kind='minutes',
         quote='Dr. Gilson discusses some options for an increase and the committee '
               'ultimately decides for a universal increase from $55 to $70 Mr. '
               'Sculimbrene makes a motion to approve the increase to $70, Mr. Beardmore '
               'seconds the motion, all approve',
         who='the School Committee, adopting the student activity fee',
         why='This is the fee being ADOPTED, and it is the sentence that settles a '
             'question this page used to get wrong. In February the committee had been '
             'shown a base fee plus per-activity fees; what it took in May was a single '
             'universal rate instead. Quoting the February proposal as the charged rate '
             'would be a proposal restated as an outcome. Note also what the motion does '
             'NOT say: it names an amount and no period, so whether $70 is a year, a term '
             'or an activity is not established here.'),
    dict(key='meals',
         board='school-committee', date='2024-06-26', doc='6632', kind='minutes',
         quote='Our students would not see any difference',
         who='the School Committee, choosing between the two free-meal programmes',
         why='Said while the committee picked the Community Eligibility Provision for '
             'Turkey Hill over the Universal Meals Program. The choice is about which '
             'scheme reimburses the district more; the point for a household is the half '
             'the sentence takes for granted — that the student is not billed either way. '
             'A charge families used to meet, and no longer do.'),
    dict(key='seventyfive',
         board='finance-committee', date='2026-03-26', doc='7737', kind='minutes',
         quote='Athletic fees would need to be raised by $75 per student. This would '
               'generate $120,000.',
         who='the Finance Committee, on the FY2027 budget',
         why='A year later, the same fee is being modelled as a way to close a budget gap — '
             'so what a family pays is not a settled schedule but a live variable. Note the '
             'unit the town itself uses when it talks about the fee: PER STUDENT. Not per '
             'sport, not per season.'),
]

# The gap-register rows this page rests on, quoted BY KEY (rule 7c). A limit whose wording
# has been changed out from under the page renders as an empty box, so a missing key stops
# the build.
GAP_KEYS = [
    'What period the school athletic family cap covers',
    'What the six fees the district’s payment portal sells actually cost',
    'What a fourth child in one family pays for high school athletics',
    'How the $1,500 athletic family cap was arrived at, and over what period',
    'What FY2027 athletic fees are for anyone other than a full-paying high school family',
    'How many children play sports',
    'Bus fees',
    'What the student activity fee is for 2026-27, and what period the $70 covers',
    'Whether the district charges anything for music, and what an instrument costs a family',
    'What the processing fee is on every school payment made online',
    'What a family spends in the cafeteria when the standard meal is free',
    'What a single-child family pays for the bus at the reduced rate in 2026-27',
]

RELATED = [
    ('athletics',
     'Both sides of the athletics money — what the fees bring in against what the town '
     'appropriates, and why an appropriation is not a cost'),
    ('athletics-ledger',
     'The revolving fund the athletic fees are paid into, at transaction level'),
    ('connecting-the-budget',
     'Why a fee paid cannot be followed to anything it bought'),
]

CENT = 0.005


def fail(msg):
    sys.exit(f'build_what_families_pay: {msg}')


def q(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a)]


def norm(s):
    return re.sub(r'\s+', ' ', s).replace('’', "'").replace('‘', "'") \
             .replace('“', '"').replace('”', '"')


def money(x):
    return None if x is None else round(float(x) + 0.0, 2)


# ------------------------------------------------------------------- the published rates

def schedule(c):
    """Every athletic rate, by year and level, with what its own source says its period is.

    The `_confirm` rows are corroborating duplicates of a minutes-sourced figure and are
    kept OUT of the pricing (they would double a rate) and IN the provenance, where they
    are the whole reason a minutes figure with no stated period can be called per season.
    """
    rows = q(c, """SELECT fy, school_year, level, item, amount, unit, unit_status,
                          unit_basis, unit_quote, set_on, source, source_file, source_ref,
                          verified
                     FROM athletic_fee_schedule ORDER BY fy, level, item""")
    if not rows:
        fail('athletic_fee_schedule is empty — a join that matches nothing looks exactly '
             'like data that is absent')
    ok = {'stated', 'structural', 'not established'}
    bad = sorted({r['unit_status'] for r in rows} - ok)
    if bad:
        fail(f'athletic_fee_schedule carries unit_status {bad} — this page renders exactly '
             f'{sorted(ok)} and would drop anything else silently')
    for r in rows:
        r['amount'] = money(r['amount'])
        r['confirming'] = r['item'].endswith('_confirm')
    return rows


def rate(rows, fy, level, item):
    hit = [r for r in rows if r['fy'] == fy and r['level'] == level
           and r['item'] == item and not r['confirming']]
    if len(hit) > 1:
        fail(f'{fy} {level} {item} appears {len(hit)} times in athletic_fee_schedule')
    return hit[0] if hit else None


def ladder(rows, fy, level):
    """The published per-child ladder for a year, where it stops, and whether it is a RULE.

    Two shapes exist in the archive and the difference is load-bearing.

    FY2026 publishes ONE rate and a PERCENTAGE — "A 25% discount for siblings" — which has
    no end: every additional child is priced by a rule the committee voted.

    FY2024, FY2025 and FY2027 publish a rate per RANK and the ladder simply stops. But the
    FY2027 rungs are not three independent numbers: 400 x 0.75 is exactly 300 and
    400 x 0.75^2 is exactly 225, to the cent, so the same 25% is compounding down the
    published ladder. That is a MEASUREMENT — the ratios are computed here and asserted
    against the discount the minutes state. Whether the rule keeps going past the third
    child is an INFERENCE, and every rung produced that way is labelled `by the ratio the
    published rates follow` wherever it is rendered.

    FY2024 and FY2025 follow no such rule: 140/250 and 85/140 are different ratios. So a
    fourth child under the old schedule is genuinely unknown, and under the new one is
    unpublished-but-implied. Those are different states and the page shows which.
    """
    first = rate(rows, fy, level, 'full_pay')
    if first is None:
        return dict(level=level, fy=fy, kind='not published', rates=[], stops_after=0,
                    pct=None, ratio=None, ratio_exact=False, source=None)
    pct = rate(rows, fy, level, 'sibling_discount_pct')
    if pct is not None:
        return dict(level=level, fy=fy, kind='percentage', pct=pct['amount'],
                    rates=[first['amount']], stops_after=1,
                    ratio=round((100.0 - pct['amount']) / 100.0, 6), ratio_exact=True,
                    source=first['source'], pct_source=pct['source'],
                    pct_ref=pct['source_ref'])
    steps = [first['amount']]
    for item in ('second_child', 'third_child'):
        r = rate(rows, fy, level, item)
        if r is None:
            break
        steps.append(r['amount'])
    ratio, exact = None, False
    if len(steps) >= 3:
        ratios = [steps[i + 1] / steps[i] for i in range(len(steps) - 1)]
        if max(ratios) - min(ratios) < 1e-9:
            ratio, exact = round(ratios[0], 6), True
            # And the rule must reproduce every published rung to the cent, not just have
            # a constant ratio -- that is the claim the page makes about these numbers.
            for n, amt in enumerate(steps):
                if abs(steps[0] * ratio ** n - amt) > CENT:
                    ratio, exact = round(ratios[0], 6), False
                    break
    return dict(level=level, fy=fy, kind='ladder', pct=None, rates=steps,
                stops_after=len(steps), ratio=ratio, ratio_exact=exact,
                source=first['source'])


# Where a rate for one child comes from. Three states, never collapsed: the archive
# publishes it; a rule the archive publishes produces it; or nothing here says.
PUBLISHED = 'published'
BY_RULE = 'by the published rule'
BY_RATIO = 'by the ratio the published rates follow'
UNKNOWN = 'unknown'


def child_rate(lad, rank, extend=True):
    """What the nth child is charged, and on what footing. RANK IS 1-BASED.

    `extend=False` gives only what a document states, which is what the scenario grid's
    "computable" flag is built on. With `extend`, a schedule whose rule is visible carries
    on past its published rungs -- and the return says so, so a page can never render an
    inferred rung as a published one.
    """
    if lad['kind'] == 'not published':
        return None, UNKNOWN
    if lad['kind'] == 'percentage':
        base = lad['rates'][0]
        if rank == 1:
            return base, PUBLISHED
        return money(base * lad['ratio']), BY_RULE
    if rank <= len(lad['rates']):
        return lad['rates'][rank - 1], PUBLISHED
    if extend and lad['ratio_exact']:
        return money(lad['rates'][0] * lad['ratio'] ** (rank - 1)), BY_RATIO
    return None, UNKNOWN


def season_charge(lad, flat, children, sports, season, extend=True):
    """What one season costs a family, before any cap.

    A child plays at most one sport in a season -- the LHS Athletics FAQ says so, and that
    rule is what makes a per-season fee also a per-sport fee at the high school. So the
    children playing in season k are those with at least k sports.

    `flat` is the reduced or waived tier: one rate for every child with no ladder, because
    nothing published applies the sibling ladder to it. Passing it is how the page prices
    the family that qualifies -- which is the other half of the argument this page answers,
    and it was missing while only full-pay families were modelled.
    """
    total, unknown, inferred = 0.0, 0, 0
    if sports < season:
        return money(0), 0, 0
    for rank in range(1, children + 1):
        if flat is not None:
            total += flat
            continue
        r, how = child_rate(lad, rank, extend=extend)
        if r is None:
            unknown += 1
        else:
            total += r
            if how in (BY_RULE, BY_RATIO):
                inferred += 1
    return money(total), unknown, inferred


def price(lad, flat, cap, children, sports, extend=True):
    """One scenario, priced BOTH WAYS, because the cap's period is not established.

    Returns the uncapped year total, the total under a per-SEASON cap and the total under
    a per-YEAR cap. Neither reading is presented as the right one anywhere this renders.
    """
    seasons, unknown, inferred = [], 0, 0
    for k in range(1, SEASONS + 1):
        charge, unk, inf = season_charge(lad, flat, children, sports, k, extend=extend)
        seasons.append(charge)
        unknown, inferred = max(unknown, unk), max(inferred, inf)
    uncapped = money(sum(seasons))
    per_season = money(sum(min(s, cap) for s in seasons)) if cap else uncapped
    per_year = money(min(uncapped, cap)) if cap else uncapped
    return dict(children=children, sports=sports, seasons=seasons, uncapped=uncapped,
                per_season=per_season, per_year=per_year,
                spread=money(per_season - per_year), unknown_child_rates=unknown,
                inferred_child_rates=inferred, computable=unknown == 0,
                fully_published=unknown == 0 and inferred == 0)


# ---------------------------------------------------------------------------- the bus

def bus(c, fy):
    rows = q(c, """SELECT item, value, value_type, source, source_file, source_ref, status
                     FROM rate_register WHERE category = 'bus_fee' AND fy = ?
                      AND item IN (%s) ORDER BY item""" % ','.join('?' * len(BUS_ITEMS)),
             fy, *BUS_ITEMS)
    if not rows:
        fail(f'rate_register carries no bus_fee rows for FY{fy} — the transport half of '
             'every scenario on this page would silently price at zero')
    got = {r['item'] for r in rows}
    if got != set(BUS_ITEMS):
        fail(f'FY{fy} bus tiers are {sorted(got)}, not the {sorted(BUS_ITEMS)} this page '
             'renders — a tier this page names would render blank')
    out = {}
    for r in rows:
        out[r['item']] = dict(
            amount=money(r['value']) if (r['value'] or '') != '' else None,
            status=r['status'], source=r['source'], source_file=r['source_file'],
            source_ref=r['source_ref'])
    return out


# ------------------------------------------------------------- what has no published price

def unpriced(c):
    """Every fee established as existing with no amount attached to it anywhere.

    This is the whole of the unknown band, and it is published as a LIST OF NAMES rather
    than as a dollar range. Rule 7: the amounts are not in this archive, so an estimate of
    them would be a proxy standing in for the thing.
    """
    rows = q(c, """SELECT fy, category, unit, item, value_type, source, source_ref, status
                     FROM rate_register
                    WHERE status IN ('not_published', 'not_adopted')
                    ORDER BY category, item""")
    if len([r for r in rows if r['status'] == 'not_published']) < 2:
        fail('rate_register carries fewer than two unpublished fees — the band above every '
             'total on this page rests on there being some, and this page states a count')
    return [dict(fy=r['fy'] or None, category=r['category'], unit=r['unit'], item=r['item'],
                 status=r['status'], source=r['source'], source_ref=r['source_ref'])
            for r in rows]


# ---------------------------------------------------------------------- what the town said

# WHAT THIS PAGE MAY AND MAY NOT CLAIM ABOUT THE SEARCH. Rule 15a says to search the
# meeting archive for what people said about a thing in the same year, and rule 13 says not
# to quote a rendering of it. The archive was being ENLARGED and RE-EXTRACTED while this
# page was written -- documents were being added and their text written out by another
# process -- so any count of how many documents were searched would have been true for a
# few minutes. It is therefore not published here at all. What IS published is the thing
# that can be checked: every quote below is asserted verbatim, on every build, against the
# named file it is attributed to. Absence of a quote on this page is not evidence that
# nobody said it.
SEARCH_NOTE = (
    'Found with scripts/search_minutes.py and asserted verbatim against the named file on '
    'every build. The coverage beside this is the scope those searches actually ran over — '
    'School Committee, 2024 onward — rather than the archive average, because a '
    'board-level search is compromised by that board\'s own scans and not by everybody '
    'else\'s. Nothing here claims that nobody else said anything: a grep that finds '
    'nothing prints nothing, and nothing reads as though nobody said it. It means nobody '
    'said it in the documents that can be read.')


SEARCH_BOARD = 'school-committee'
SEARCH_SINCE = '2024-01-01'


def coverage():
    """How many in-scope documents the fee searches could actually read (rule 15a).

    The denominator ships with the finding because a grep that finds nothing prints
    nothing, and nothing reads as `nobody said it`.
    """
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import search_minutes as sm
    rows = [r for r in sm.index()
            if SEARCH_BOARD in (r['_stem'] or r['board']).lower().replace(' ', '-')
            and r['date'] >= SEARCH_SINCE]
    if not rows:
        fail('no School Committee documents are in scope for the fee searches — the page '
             'publishes how many were searched, and a denominator of zero would read as '
             'complete coverage')
    for r in rows:
        if r['_has_text']:
            sm.body_of(r)
    searched = [r for r in rows if r['_searchable']]
    return dict(board='School Committee', since=SEARCH_SINCE,
                scope=len(rows), searched=len(searched),
                unsearchable=len([r for r in rows if r['_held'] and not r['_searchable']]),
                not_held=len([r for r in rows if not r['_held']]),
                pct=round(100.0 * len(searched) / len(rows), 1))


def said():
    out = []
    for spec in QUOTES:
        rel = f'{MINUTES}/{spec["board"]}/{spec["date"]}-{spec["kind"]}-{spec["doc"]}.txt'
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail(f'{rel} is not here — a quote on this page is attributed to a document '
                 'that is not in the archive')
        text = norm(open(path, encoding='utf-8', errors='replace').read())
        if norm(spec['quote']) not in text:
            fail(f'the quote attributed to {spec["board"]} {spec["date"]} is no longer in '
                 f'{rel} — quote the source, never your rendering of it')
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], who=spec['who'], why=spec['why'],
            cite=f'/docs/{rel.replace("sources/", "")}',
            town=f'https://www.lunenburgma.gov/AgendaCenter/ViewFile/'
                 f'{"Minutes" if spec["kind"] == "minutes" else "Agenda"}/'
                 f'_{spec["date"][5:7]}{spec["date"][8:10]}{spec["date"][:4]}-{spec["doc"]}'))
    return out


def faq_rule():
    """The FAQ sentence the per-sport reading rests on, quoted rather than paraphrased."""
    path = os.path.join(ROOT, FAQ_REL)
    if not os.path.exists(path):
        fail(f'{FAQ_REL} is not on disk — run scripts/sync_archive.py --pull')
    text = norm(open(path, encoding='utf-8', errors='replace').read())
    quotes = ['Only one sport per season is allowed.',
              'Total Cap per season=$475.00',
              'Per Season Breakdown:']
    for qt in quotes:
        if norm(qt) not in text:
            fail(f'the LHS Athletics FAQ no longer contains {qt!r} — this page quotes it '
                 'as the source of a unit')
    return dict(cite=f'/docs/{FAQ_REL.replace("sources/", "")}', quotes=quotes,
                title='LHS Athletics FAQ (rschoolteams.com)')


# ==========================================================================================
#                        WHAT A HOUSEHOLD PAYS, AS ONE TABLE
# ==========================================================================================
# THE QUESTION THIS PAGE ANSWERS is what it costs a household to have children in Lunenburg
# schools for a year, over and above what the household pays in property tax. Athletics is
# ONE ROW of that. It was the whole page for a while because it is the fee with a schedule,
# a vote and a set of minutes behind it -- which is a fact about the archive, not about a
# family's bank statement.
#
# THE TOTAL IS A FLOOR, AND THE FLOOR IS THE ARGUMENT. Charges fall into four bands and the
# table shows all four, because a clean total would be a less honest number than a partial
# one with the missing pieces named:
#
#   priced     an amount a document states, for the year selected
#   carried    charged, and the last rate set in public is from an earlier year and has not
#              been restated for this one. The student activity fee is the case: voted to
#              $70 on 7 May 2025 and not restated since
#   unpriced   charged, and NO amount is published anywhere in this archive. Eight of these,
#              six of them products the district's own payment portal sells
#   no charge  a charge a family might expect and does not pay. School meals are free under
#              the state's universal meals programme, and that belongs in the table at full
#              size -- rule 8: the record shows the town and the state lowering a household
#              bill and that is as much a finding as a fee going up
#
# RULE 11, POINTED AT HOUSEHOLDS. Every figure here is money a family hands over. It is NOT
# what the thing costs the district, and it does not reduce the appropriation one-for-one --
# several of these budget lines are recorded already net of the fee. "What a family pays"
# and "what the town is spared" are two questions and this answers only the first.
#
# WHAT IT REFUSES TO WRITE ON. Every lookup below is a join that could match nothing, and a
# join that matches nothing looks exactly like a charge that does not exist.

# The bands, in the order the table renders them.
PRICED, CARRIED, UNPRICED, NOCHARGE = 'priced', 'carried', 'unpriced', 'no charge'

# The household a reader can describe. Deliberately small: these are the questions a parent
# can answer about their own family without looking anything up.
HH_CHILDREN = [1, 2, 3, 4]
HH_SPORTS = [0, 1, 2, 3]
HH_LEVELS = ['HS', 'MS']
HH_TIERS = ['full', 'reduced', 'waived']

# What the register must still carry for this table to mean anything. Named rather than
# discovered, so a row disappearing is a build failure and not a shorter table.
NEEDED = [
    ('activity_fee', 'student activity fee'),
    ('meals', 'standard school meal'),
    ('other_fee', 'online payment processing fee'),
    ('other_fee', 'instruments, reeds and supplies'),
    ('meals', 'a la carte and second meals'),
]

# The charges that are always on the table and never vary with the household, because
# nothing published says what any of them costs. Each carries what a request would have to
# ASK FOR -- rule 7c's "closes:", written as an instruction rather than as a complaint.
# A charge moves out of this list by acquiring a value in the register; nothing else changes.
REQUESTS = {
    'Afterschool Activity Fee':
        'the afterschool activity fee schedule for 2026-27, per child and per session, and '
        'whether it is charged per programme or per term',
    'Chromebook Repair Fee':
        'the device damage and repair fee schedule, per incident, and whether a deductible '
        'or an insurance option exists',
    'Extended Day & ELC':
        'the Extended Day and Early Learning Center rate card for 2026-27 — per day, per '
        'week or per month, with any sibling rate',
    'Field Trips':
        'the field trip charges billed to families by school and grade for 2026-27, and '
        'the policy where a family cannot pay',
    'LHS Parking Permit':
        'the published high school parking permit rate for 2026-27 and the period it '
        'covers — a resident states $50 in public comment and no schedule is published',
    'Primary Preschool Program':
        'the preschool tuition rate card for 2026-27, per session and per week, with the '
        'sliding scale if there is one',
    'instruments, reeds and supplies':
        'whether the district charges any music fee or instrument rental at all, and its '
        'rate per student per year if it does',
    'a la carte and second meals':
        'the cafeteria a la carte price list — the items a family pays for even though the '
        'standard meal is free',
    'online payment processing fee':
        'the RevTrak processing rate — a percentage, a flat amount per transaction, or '
        'both — since it is added to every fee above',
    'athletic fee schedule':
        'the athletic fee schedule as published to families for 2026-27 — every rank of '
        'the sibling ladder including the fourth child, the reduced and waived tiers, and '
        'the period the $1,500 family cap covers',
    'student activity fee':
        'the adopted student activity fee for 2026-27, and whether $70 is per student per '
        'year, per activity, or a base fee with activity fees on top',
}


def reg(c):
    """The register, keyed on the pair that is actually unique."""
    rows = q(c, """SELECT fy, category, unit, item, value, value_type, set_on, source,
                          source_file, source_ref, status
                     FROM rate_register""")
    if not rows:
        fail('rate_register is empty — every non-athletic charge on this page reads from '
             'it, and the table would render as athletics alone with no sign anything was '
             'missing')
    for r in rows:
        r['amount'] = money(r['value']) if (r['value'] or '') != '' else None
    have = {(r['category'], r['item']) for r in rows}
    gone = [n for n in NEEDED if n not in have]
    if gone:
        fail('rate_register no longer carries ' + '; '.join(f'{a}/{b}' for a, b in gone) +
             ' — this page renders each of those as a named row of a household bill, and a '
             'lookup that matches nothing would silently drop the charge')
    # AND THE ASSERTION THAT COMES OUT OF A CORRECTION (WRITING-AN-ANALYSIS, "when a
    # correction happens"). This page once recorded the student activity fee as proposed
    # and never voted, on the strength of the February 2025 minute, while the May 2025
    # minute adopting it sat unread in the same folder. A fee a family demonstrably pays,
    # described as not existing, is the worst thing this page can say — so an adopted
    # activity fee with an amount is now a precondition of building it at all.
    voted = [r for r in rows if r['category'] == 'activity_fee'
             and r['amount'] is not None and r['status'] in ('verified', 'recorded')]
    if not voted:
        fail('rate_register carries no student activity fee with an amount — this page '
             'once said the fee was proposed and never adopted while the minute adopting '
             'it was in the archive, and it is charged. Do not render a fee families pay '
             'as one that does not exist')
    return rows


def pick(rows, category, item, fy=None):
    hit = [r for r in rows if r['category'] == category and r['item'] == item
           and (fy is None or str(r['fy']) == str(fy))]
    if len(hit) > 1:
        fail(f'{category}/{item}{"" if fy is None else f" FY{fy}"} appears {len(hit)} times '
             'in rate_register — a bill row would take whichever came back first')
    return hit[0] if hit else None


def cite_of(r):
    f = r.get('source_file') or ''
    return f'/docs/{f}' if f and not f.startswith('http') else (r.get('source_ref') or None)


# EVERY BILL ROW IS TWO THINGS, and they are stored apart because one of them repeats.
# `DEFS` holds what is constant for a charge -- its label, who it applies to, the document
# behind it, the request that would price it. A bill row holds only what changes with the
# household: the band, the amount, and the sentence naming the figures in it. There are
# several hundred priced households and one catalogue, and merging the two multiplied the
# same paragraph of provenance across the whole file. `charge_defs` is emitted once and the
# page joins on `id`.
DEFS = {}


def define(cid, label, basis='', r=None, applies='', request=None):
    """Register the constant half of a charge. Idempotent, and refuses to disagree."""
    d = dict(id=cid, label=label, applies=applies,
             basis=basis or (r['source'] if r else ''),
             status=(r['status'] if r else ''),
             quote=(r['source_ref'] if r else None),
             cite=(cite_of(r) if r else None), request=request)
    prev = DEFS.get(cid)
    if prev is not None and prev != d:
        # Two households disagreeing about what a charge IS means the id is not identifying
        # one charge, and the page would render whichever was written last.
        fail(f'charge {cid!r} is defined two different ways — an id that does not identify '
             'one charge would render a different provenance depending on the household')
    DEFS[cid] = d
    return cid


def charge_row(cid, label, band, amount=None, detail='', basis='', r=None, note='',
               request=None, applies=''):
    """One line of a household's bill: only what varies with the household."""
    define(cid, label, basis=basis, r=r, applies=applies, request=request)
    row = dict(id=cid, band=band, amount=amount, detail=detail, note=note)
    return row


def standing_charges(rows, fy):
    """The rows that are on every household's table whatever the household looks like.

    They are hoisted out of the per-scenario bills because they do not vary with the
    scenario -- and because a charge nobody publishes an amount for cannot vary with
    anything, which is the point being made.
    """
    out = []
    meal = pick(rows, 'meals', 'standard school meal', fy) \
        or pick(rows, 'meals', 'standard school meal')
    out.append(charge_row(
        'meals', 'School meals', NOCHARGE, amount=meal['amount'], r=meal,
        detail='free to every student', applies='every child, every school day',
        note='Massachusetts funds universal free school meals, and the district takes the '
             'programme. This row is $0 because a family is not billed for the standard '
             'meal — not because nothing was looked for.'))
    for r in sorted([x for x in rows if x['status'] == 'not_published'
                     and x['category'] in ('other_fee', 'meals')],
                    key=lambda x: x['item']):
        out.append(charge_row(
            f"unpriced:{r['item']}", r['item'], UNPRICED, r=r,
            detail='charged — no amount published',
            applies=r['unit'], request=REQUESTS.get(r['item'])))
    if len(out) < 5:
        fail('fewer than four unpriced household charges survive in rate_register — the '
             'floor this page publishes rests on there being some, and the page states '
             'their count')
    missing = [DEFS[o['id']]['label'] for o in out
               if o['band'] == UNPRICED and not DEFS[o['id']]['request']]
    if missing:
        fail('no records request is written for: ' + '; '.join(missing) + ' — rule 7c: a '
             'gap with no named remedy is a grievance, and a gap with one is a request')
    return out


def bill(rows, lad, flat, capamt, fy, level, children, sports, tier, bus_on, activities,
         parking):
    """One household, priced. Returns the rows that VARY, plus the three totals.

    Three totals rather than one, and the difference between them is the honest part:
      floor          only amounts a document states for this year
      carried        charged, last set in public in an earlier year, not restated for this
      floor_carried  the two added, which is the closest thing to a complete bill that the
                     published record supports
    """
    out = []

    # --- athletics. One row, priced from the same ladder the rest of this page uses. The
    # cap's period is not stated, so where the two readings differ the row carries a RANGE
    # and a footnote -- it qualifies this line and belongs beside it, not above the page.
    if sports > 0:
        g = price(lad, flat, capamt, children, sports)
        lo, hi = sorted((g['per_year'], g['per_season']))
        out.append(charge_row(
            f'athletics:{fy}:{level}:{tier}', 'Athletics',
            PRICED if g['computable'] else UNPRICED,
            amount=g['per_year'] if g['computable'] else None,
            detail=(f'{children} child{"" if children == 1 else "ren"}, '
                    f'{sports} season{"" if sports == 1 else "s"} each, '
                    + ('one fee per child per season' if tier == 'full'
                       else f'at the {tier} rate')),
            applies='each child who plays a sport, each season they play',
            basis=lad['source'] or 'athletic_fee_schedule',
            note=('The $1,500 family cap states no period. Read per year this family pays '
                  f'{money(lo):,.2f}; read per season, {money(hi):,.2f}. Nothing published '
                  'says which, and no ordinary family reaches the cap either way.'
                  if hi > lo else ''),
            request=REQUESTS['athletic fee schedule']))
        out[-1]['low'], out[-1]['high'] = money(lo), money(hi)
        out[-1]['inferred'] = g['inferred_child_rates'] > 0

    # --- the bus. A FAMILY rate, not a per-child one, which is why a second child riding
    # costs $90 and a second child playing a sport costs $300.
    if bus_on:
        if tier == 'waived':
            item = 'qualifying families'
        elif children == 1:
            item = 'one student, reduced' if tier == 'reduced' else 'one student'
        else:
            item = 'two or more, reduced' if tier == 'reduced' else 'two or more students'
        # A tier this year does not restate falls back to the last year that did, and the
        # row says so. FY2027's email gives three tiers and drops the single-student
        # reduced rate, which is exactly this case.
        b = pick(rows, 'bus_fee', item, fy)
        fallback = b is None or b['amount'] is None
        if fallback:
            b = pick(rows, 'bus_fee', item, 2026) or b
        if b is None:
            fail(f'rate_register has no bus_fee tier {item!r} for FY{fy} or FY2026 — a '
                 'household that rides the bus would be billed nothing and look cheap')
        carried = fallback or str(b['fy']) != str(fy)
        band = UNPRICED if b['amount'] is None else (CARRIED if carried else PRICED)
        out.append(charge_row(
            f'bus:{item}:{b["fy"]}', 'Bus to school', band,
            amount=b['amount'], r=b,
            detail='one charge for the whole family, however many children ride',
            applies='grades 7-12, and K-6 living under two miles from school',
            request=('the adopted transportation fee schedule for 2026-27, with every '
                     'tier — including the reduced rate for a single-child family, which '
                     'the August 2026 email does not restate'
                     if b['amount'] is None else None),
            note=(f'FY{fy} does not restate this tier; this is the FY{b["fy"]} rate.'
                  if carried and b['amount'] is not None else '')))

    # --- the student activity fee. VOTED, and the amount is real. What is not established
    # is the period or the base, so the row says $70 a child and says the minute does not.
    a_now = pick(rows, 'activity_fee', 'student activity fee', fy)
    a_last = pick(rows, 'activity_fee', 'student activity fee', 2026)
    if activities and a_last is not None:
        use = a_now if (a_now and a_now['amount'] is not None) else a_last
        carried = use is not a_now or a_now['amount'] is None
        out.append(charge_row(
            f'activity:{use["fy"]}', 'Student activity fee',
            CARRIED if carried else PRICED,
            amount=money(use['amount'] * children), r=use,
            detail=f'${use["amount"]:,.2f} a child, {children} '
                   f'child{"" if children == 1 else "ren"}',
            applies='a child who joins a club or a student activity',
            request=REQUESTS['student activity fee'],
            note=('Voted to $%s on 7 May 2025 and not restated for FY%s. The motion names '
                  'an amount and no period, so whether this is once a year, once a term or '
                  'once per activity is not established.' % (f'{use["amount"]:,.0f}', fy)
                  if carried else
                  'The motion names an amount and no period — whether it is charged once a '
                  'year, once a term or once per activity is not established.')))

    # --- parking. A resident's own figure, said in public comment. It is not a schedule and
    # the row says so rather than promoting it to one (rule 13a).
    if parking and level == 'HS':
        pk = pick(rows, 'other_fee',
                  'parking permit, as stated by a resident in public comment')
        if pk is None:
            fail('the parking figure is gone from rate_register — the row would vanish '
                 'from every high school bill with nothing marking its absence')
        out.append(charge_row(
            'parking', 'High school parking permit', CARRIED, amount=pk['amount'], r=pk,
            detail='one student driving to school',
            applies='a high school student who drives',
            request=REQUESTS['LHS Parking Permit'],
            note='This is a resident stating in public comment what they paid, not a '
                 'schedule the district published. The portal sells a parking permit and '
                 'prints no amount.'))

    floor = money(sum(r['amount'] for r in out
                      if r['band'] == PRICED and r['amount'] is not None))
    carried_amt = money(sum(r['amount'] for r in out
                            if r['band'] == CARRIED and r['amount'] is not None))
    return dict(rows=out, floor=floor, carried=carried_amt,
                floor_carried=money(floor + carried_amt),
                unpriced_in_bill=len([r for r in out if r['band'] == UNPRICED]))


def hh_key(fy, level, children, sports, tier, bus_on, activities, parking):
    return (f'{fy}|{level}|{children}|{sports}|{tier}|{int(bus_on)}|{int(activities)}'
            f'|{int(parking)}')


def households(c, rows, years):
    """Every household a reader can describe, priced. Small enough to ship as one file."""
    by_fy = {y['fy']: y for y in years}
    bills = {}
    for fy in YEARS:
        y = by_fy[fy]
        cap = (y['cap'] or {}).get('amount') or 0
        for level in HH_LEVELS:
            lv = y['levels'][level]
            for tier in HH_TIERS:
                t = lv['tiers'][tier]
                if not t['available']:
                    continue
                flat = t['flat'] if tier != 'full' else None
                if tier == 'waived':
                    flat = 0.0
                for children in HH_CHILDREN:
                    for sports in HH_SPORTS:
                        for bus_on in (False, True):
                            for activities in (False, True):
                                for parking in ((False, True) if level == 'HS'
                                                else (False,)):
                                    k = hh_key(fy, level, children, sports, tier, bus_on,
                                               activities, parking)
                                    bills[k] = bill(rows, lv['ladder'], flat, cap, fy,
                                                    level, children, sports, tier, bus_on,
                                                    activities, parking)
    if not bills:
        fail('no household could be priced — the table is the page and there would be '
             'nothing on it')
    return bills


# ------------------------------------------------------------------- what this establishes

def dollars(n):
    """A fee, rendered. `C.usd` is whole dollars, and a school fee has cents in it --
    $812.50 is a bill somebody pays and $813 is one nobody does."""
    n = float(n)
    return C.usd(n) if abs(n - round(n)) < CENT else '$%s' % format(n, ',.2f')


def the_conclusions(rows, register, lad27, discount_pct, contrast, hh_bills,
                    hh_default, unpriced_named):
    """The three claims this report makes, with every figure in them registered.

    WHAT THIS PAGE OWES A FAMILY IS A NUMBER: what a year in the Lunenburg schools costs
    their household. So that is what leads, and the second and third conclusions are the
    two things that change it most -- which tier the family is in, and how many children
    are in it. An earlier draft led instead on the family cap stating no period. That
    sentence is true and it is about a defect in a document rather than about anybody's
    bank statement; it is a footnote, it lives in the athletics row's own note and in
    `money_gaps`, and it is not a conclusion.
    """
    def bill_for(children):
        k = hh_key(hh_default['fy'], hh_default['level'], children,
                   hh_default['sports'], hh_default['tier'], hh_default['bus'],
                   hh_default['activities'], hh_default['parking'])
        if k not in hh_bills:
            fail(f'the household {k} was not priced — a conclusion on this page states '
                 'what it costs, and a lookup that matched nothing would state nothing')
        return hh_bills[k]

    def row_of(b, cid):
        # The bill rows carry composite ids -- `bus:two or more students:2027` --
        # because two rows of one bill can be the same kind of charge. Matched on
        # the KIND, and asserted to be exactly one, so a renamed id fails here
        # rather than quietly dropping the figure a conclusion states.
        hit = [r for r in b['rows'] if r['id'].split(':')[0] == cid]
        if len(hit) != 1 or hit[0]['amount'] is None:
            fail(f'the {cid!r} line is not on the household bill this page draws a '
                 'conclusion from — the conclusion states its amount')
        return hit[0]['amount']

    one, two, three = bill_for(1), bill_for(2), bill_for(3)
    second_costs = money(two['floor_carried'] - one['floor_carried'])
    third_costs = money(three['floor_carried'] - two['floor_carried'])
    bus_one, bus_two = row_of(one, 'bus'), row_of(two, 'bus')
    activity_one = row_of(one, 'activity')
    if second_costs <= 0 or third_costs <= 0:
        fail('an additional child now costs a Lunenburg family nothing — the marginal-child '
             'conclusion states that it costs something and would have to be rewritten')

    return emit('what-families-pay', [
        conclusion(
            id='what-a-family-actually-pays',
                bearing='lever',
            claim='A year for two high schoolers, one sport each, riding the bus and joining a club',
            so_what='Athletic fees, the bus and student activity fees. Several other charges have no published amount.',
            lede='Two Lunenburg high schoolers, one sport each, riding the bus and '
                  'joining a club, cost their family %s in %s: %s in athletic fees, %s '
                  'for the bus and %s in student activity fees.'
                  % (dollars(two['floor_carried']), C.fy(hh_default['fy']),
                     dollars(row_of(two, 'athletics')), dollars(bus_two),
                     dollars(row_of(two, 'activity'))),
            detail='The athletic fee is charged per child per season — %s for the first '
                   'child and %s for the second, the %s sibling discount the School '
                   'Committee voted, compounding. The bus is one charge for the whole '
                   'family however many children ride. The activity fee is %s a child and '
                   'was last set in public for an earlier year. And %s is a FLOOR: %s '
                   'further charges a Lunenburg family can meet — preschool, extended '
                   'day, field trips, device repair among them — are sold by the district '
                   'with no published amount anywhere in this archive, so no family and no '
                   'committee can total a school year exactly.'
                   % (dollars(lad27['rates'][0]), dollars(lad27['rates'][1]),
                      C.pct(discount_pct, 0), dollars(activity_one),
                      dollars(two['floor_carried']), C.num(unpriced_named)),
            figures={
                'total': figure(two['floor_carried'], dollars(two['floor_carried'])),
                'fy': figure(hh_default['fy'], C.fy(hh_default['fy'])),
                'athletics': figure(row_of(two, 'athletics'),
                                    dollars(row_of(two, 'athletics'))),
                'bus': figure(bus_two, dollars(bus_two)),
                'activity': figure(row_of(two, 'activity'),
                                   dollars(row_of(two, 'activity'))),
                'first_child': figure(lad27['rates'][0], dollars(lad27['rates'][0])),
                'second_child': figure(lad27['rates'][1], dollars(lad27['rates'][1])),
                'discount': figure(discount_pct, C.pct(discount_pct, 0)),
                'activity_each': figure(activity_one, dollars(activity_one)),
                'unpriced': figure(unpriced_named, C.num(unpriced_named)),
            },
            figure='total',
            kind='measured',
            basis='The athletic rate for the year now running is the superintendent’s '
                  'August 2026 email to families, as `athletic_fee_schedule` records it; '
                  'the bus tiers are the superintendent’s transport email for the same '
                  'year; the student activity fee is the School Committee’s own vote, in '
                  'the minutes, and has not been restated since. Every rate is held in '
                  '`rate_register` with the document and the quoted line it came from.',
            not_shown='What the schools cost. A fee is money in, and the budget lines it '
                      'offsets are already recorded net of it, so what a family pays and '
                      'what the town is spared are two different questions and only the '
                      'first is answered here. It also does not say whether this is too '
                      'much: that is the argument, and this is the arithmetic under it.',
            see=[('/what-sports-cost', 'both sides of the athletics money'),
                 ('/rate-register', 'every rate, with the document that set it')],
        ),
        conclusion(
            id='parents-is-not-one-group',
                bearing='sizes',
            claim='A year for three children playing one sport each, at the full rate',
            so_what='Another family pays a fraction of that for the same children. Parents are not one group.',
            lede='The same %s children playing one sport each cost one Lunenburg family '
                  '%s a year and another %s — a factor of %s between two households at '
                  'the same school.'
                  % (C.num(contrast['children']), dollars(contrast['full']),
                     dollars(contrast['reduced']), '%.2f' % contrast['ratio']),
            detail='%s is the most recent year in which both rates are published. A family '
                   'that qualifies pays a flat %s a child a season with no sibling ladder '
                   'at all, and a family whose fee is waived pays %s. So the argument that '
                   '“parents should pay more” is really an argument about which parents: '
                   'the same children in the same uniforms are a completely different bill '
                   'depending on the household they belong to, and the argument is usually '
                   'made without any of these figures in it.'
                   % (C.fy(contrast['fy']), dollars(contrast['flat']),
                      dollars(contrast['waived'])),
            figures={
                'children': figure(contrast['children'], C.num(contrast['children'])),
                'full': figure(contrast['full'], dollars(contrast['full'])),
                'reduced': figure(contrast['reduced'], dollars(contrast['reduced'])),
                'ratio': figure(contrast['ratio'], '%.2f' % contrast['ratio']),
                'fy': figure(contrast['fy'], C.fy(contrast['fy'])),
                'flat': figure(contrast['flat'], dollars(contrast['flat'])),
                'waived': figure(contrast['waived'], dollars(contrast['waived'])),
            },
            figure='full',
            kind='measured',
            basis='The School Committee’s vote of 26 February 2025, in the minutes, which '
                  'sets the full rate, the reduced rate and the sibling discount in one '
                  'motion; and the LHS Athletics FAQ, which is the only document in this '
                  'archive stating that a fee can be waived to nothing.',
            not_shown='How many families are in each tier. Nothing published counts them, '
                      'so this prices the three households and cannot weight them. The '
                      'full-paying family’s second and third children are priced by the '
                      'discount the committee voted rather than by a printed rate, and for '
                      'the year now running the district publishes no reduced or waived '
                      'rate at all, so the cheaper half of the comparison cannot be drawn '
                      'for the current year.',
            see=[('/what-sports-cost', 'what the fees bring in against what the town '
                                       'appropriates'),
                 ('/what-we-cannot-answer', 'the rates nobody publishes')],
        ),
        conclusion(
            id='the-second-child-does-not-double-the-bill',
            bearing='lever',
            claim='What a second child adds to a family’s school bill',
            so_what='Not another full share: the bus is one charge per family, and each athlete after the first pays less.',
            lede='A second child costs a Lunenburg family %s more and a third %s more — '
                  'not another %s each — because the bus is one charge for the whole '
                  'family and every athlete after the first pays %s less than the one '
                  'before.'
                  % (dollars(second_costs), dollars(third_costs),
                     dollars(one['floor_carried']), C.pct(discount_pct, 0)),
            detail='One high school child playing a sport, riding the bus and joining a '
                   'club is %s in %s. Two are %s and three are %s. The bus is %s for one '
                   'child and %s for any number, so the second child adds %s there and the '
                   'third adds nothing; athletics falls %s, %s, %s down the ladder; only '
                   'the activity fee, at %s a child, is flat. Which charges are per family '
                   'and which are per child is what decides what a larger household pays, '
                   'and it is the part of the schedule nobody argues about.'
                   % (dollars(one['floor_carried']), C.fy(hh_default['fy']),
                      dollars(two['floor_carried']), dollars(three['floor_carried']),
                      dollars(bus_one), dollars(bus_two), dollars(bus_two - bus_one),
                      dollars(lad27['rates'][0]), dollars(lad27['rates'][1]),
                      dollars(lad27['rates'][2]), dollars(activity_one)),
            figures={
                'second': figure(second_costs, dollars(second_costs)),
                'third': figure(third_costs, dollars(third_costs)),
                'one_child': figure(one['floor_carried'],
                                    dollars(one['floor_carried'])),
                'discount': figure(discount_pct, C.pct(discount_pct, 0)),
                'fy': figure(hh_default['fy'], C.fy(hh_default['fy'])),
                'two_children': figure(two['floor_carried'],
                                       dollars(two['floor_carried'])),
                'three_children': figure(three['floor_carried'],
                                         dollars(three['floor_carried'])),
                'bus_one': figure(bus_one, dollars(bus_one)),
                'bus_two': figure(bus_two, dollars(bus_two)),
                'bus_step': figure(bus_two - bus_one, dollars(bus_two - bus_one)),
                'rung1': figure(lad27['rates'][0], dollars(lad27['rates'][0])),
                'rung2': figure(lad27['rates'][1], dollars(lad27['rates'][1])),
                'rung3': figure(lad27['rates'][2], dollars(lad27['rates'][2])),
                'activity_each': figure(activity_one, dollars(activity_one)),
            },
            figure='second',
            kind='measured',
            basis='The three bills are computed from the same rates as the rest of this '
                  'page — the athletic ladder as the superintendent’s August 2026 email '
                  'publishes it, the bus tiers from the transport email, and the student '
                  'activity fee from the School Committee vote — one household at a time, '
                  'and differenced.',
            not_shown='A fourth child. The published ladder stops at the third, and the '
                      'rung below it is produced by carrying the voted discount on rather '
                      'than by any document. It also assumes every child plays and every '
                      'child rides, which is a household a reader chooses on the page '
                      'rather than a typical one.',
            see=[('/what-we-cannot-answer', 'what a fourth child pays, and the rest of the '
                                            'register'),
                 ('/rate-register', 'every rate, with the document that set it')],
        ),
    ])


# --------------------------------------------------------------------------- the build

def build():
    if not os.path.exists(DB):
        fail(f'{os.path.relpath(DB, ROOT)} is not here — run scripts/build_db.py')
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row

    rows = schedule(c)

    # ---- the caps, and what each one's own source says about its period ----------------
    caps = []
    for fy in CAP_YEARS:
        hit = [r for r in rows if r['fy'] == fy and r['item'] == 'family_cap']
        if not hit:
            fail(f'no family_cap in athletic_fee_schedule for FY{fy} — this page compares '
                 'that year’s cap against the others by name')
        r = hit[0]
        lad = ladder(rows, fy, 'HS')
        three = [x for x, _ in (child_rate(lad, n, extend=False) for n in (1, 2, 3))
                 if x is not None]
        caps.append(dict(
            fy=fy, school_year=r['school_year'], amount=r['amount'], level=r['level'],
            unit=r['unit'], unit_status=r['unit_status'], unit_basis=r['unit_basis'],
            unit_quote=r['unit_quote'] or None, source=r['source'],
            source_file=r['source_file'] or None, source_ref=r['source_ref'] or None,
            verified=r['verified'], ladder=three,
            ladder_sum=money(sum(three)) if len(three) == 3 else None,
            ladder_complete=len(three) == 3,
            headroom=(money(r['amount'] - sum(three)) if len(three) == 3 else None)))

    stated = [x for x in caps if x['unit_status'] == 'stated']
    unstated = [x for x in caps if x['unit_status'] != 'stated']
    if not stated or not unstated:
        fail('every family cap now carries the same unit_status — the comparison this page '
             'is built on is that one cap states its period and the later ones do not')

    # ---- THE EXHIBIT. One sport each, one season, the ladder carried past what is
    # published -- BOTH WAYS, because the conclusion has to survive the choice between
    # them. `by_rule` keeps the 25% compounding that reproduces the three published rungs
    # to the cent; `flat` is the more expensive assumption, that the discount stops
    # descending and every further child pays the third-child rate. Neither is published
    # and the page says so on the rows themselves.
    lad27 = ladder(rows, 2027, 'HS')
    cap27 = next(x for x in caps if x['fy'] == 2027)
    if lad27['kind'] != 'ladder' or lad27['stops_after'] != 3:
        fail('the FY2027 high school ladder is no longer three published steps — the '
             'fourth-child finding and the ladder exhibit both rest on where it stops')
    if not lad27['ratio_exact']:
        fail('the FY2027 published rates no longer follow one constant ratio — the page '
             'states that 400 x 0.75 and 400 x 0.75^2 reproduce them to the cent, and '
             'every inferred rung below is produced by that ratio')
    lad26 = ladder(rows, 2026, 'HS')
    if lad26['kind'] != 'percentage' or abs(lad26['ratio'] - lad27['ratio']) > 1e-9:
        fail('the FY2027 ladder ratio is no longer the FY2026 sibling discount the '
             'committee voted — that identity is what lets an unpublished rung be called '
             'inferred rather than unknown')
    flat_rate = lad27['rates'][-1]
    ladder_exhibit, by_rule, by_flat = [], 0.0, 0.0
    for n in range(1, LADDER_CHILDREN + 1):
        published = n <= lad27['stops_after']
        r_rule, how = child_rate(lad27, n)
        r_flat = lad27['rates'][n - 1] if published else flat_rate
        by_rule += r_rule
        by_flat += r_flat
        ladder_exhibit.append(dict(
            children=n, published=published, footing=how,
            rate_by_rule=money(r_rule), rate_flat=money(r_flat),
            cumulative_by_rule=money(by_rule), cumulative_flat=money(by_flat),
            under_cap=by_flat < cap27['amount'],
            headroom_by_rule=money(cap27['amount'] - by_rule),
            headroom_flat=money(cap27['amount'] - by_flat)))
    if not ladder_exhibit[-1]['under_cap']:
        fail(f'{LADDER_CHILDREN} children at one sport each now reach the FY2027 cap on '
             'the more expensive of the two assumptions — the page’s lead inference is '
             'that they do not, and it must be rewritten rather than re-rendered')

    # ---- the scenarios, both cap readings, three fee tiers, every year and level --------
    # THE TIERS ARE THE POINT OF THIS SECTION. "Parents" is not one group: the same three
    # children cost a full-paying family $925 a season and a qualifying family $150, and
    # the argument this page answers is usually made without either figure.
    years = []
    for fy in YEARS:
        cap = next((x for x in caps if x['fy'] == fy), None)
        capamt = cap['amount'] if cap else 0
        levels = {}
        for level in ('HS', 'MS'):
            lad = ladder(rows, fy, level)
            red = rate(rows, fy, level, 'reduced_fee')
            tiers = {}
            for tier, flat in (('full', None),
                               ('reduced', red['amount'] if red else None),
                               ('waived', 0.0)):
                available = tier == 'full' or flat is not None
                grid = ([price(lad, flat, capamt, ch, sp)
                         for ch in range(1, MAX_CHILDREN + 1)
                         for sp in range(0, MAX_SPORTS + 1)] if available else [])
                tiers[tier] = dict(
                    available=available,
                    flat=money(flat) if flat is not None and tier != 'full' else None,
                    source=(red['source'] if tier == 'reduced' and red else
                            FAQ_WAIVER if tier == 'waived' else lad['source']),
                    source_ref=(red['source_ref'] if tier == 'reduced' and red else None),
                    grid=grid,
                    max_spread=money(max((g['spread'] for g in grid if g['computable']),
                                         default=0)),
                    season_cap_ever_binds=any(g['computable'] and max(g['seasons']) > capamt
                                              for g in grid),
                    uncomputable=[dict(children=g['children'], sports=g['sports'])
                                  for g in grid if not g['computable']],
                    inferred=[dict(children=g['children'], sports=g['sports'])
                              for g in grid if g['computable']
                              and not g['fully_published']])
            levels[level] = dict(
                ladder=lad,
                reduced=red['amount'] if red else None,
                reduced_status='published' if red else 'not published',
                tiers=tiers)
        years.append(dict(fy=fy, cap=cap, levels=levels, bus=bus(c, fy)))

    def cells(pred=lambda g: True):
        for y in years:
            for lv in ('HS', 'MS'):
                for tier, t in y['levels'][lv]['tiers'].items():
                    for g in t['grid']:
                        if pred(g):
                            yield y, lv, tier, g

    hs27 = next(y for y in years if y['fy'] == 2027)['levels']['HS']
    max_spread = money(max((g['spread'] for *_, g in cells(lambda g: g['computable'])),
                           default=0))
    spread_at = next((dict(fy=y['fy'], level=lv, tier=tier, children=g['children'],
                           sports=g['sports'])
                      for y, lv, tier, g in cells(lambda g: g['computable'])
                      if g['spread'] == max_spread), None)
    # AND THE SAME FIGURE OVER SCENARIOS WITH NO INFERRED RUNG IN THEM. The widest gap
    # overall sits in a four-child family, whose fourth rate is inferred rather than
    # published; the headline must not rest on that. This is the widest gap between the two
    # readings where every rate in the scenario is one a document states.
    published_spread = money(max((g['spread'] for *_, g in
                                  cells(lambda g: g['fully_published'])), default=0))
    published_spread_at = next(
        (dict(fy=y['fy'], level=lv, tier=tier, children=g['children'], sports=g['sports'])
         for y, lv, tier, g in cells(lambda g: g['fully_published'])
         if g['spread'] == published_spread), None)
    if published_spread <= 0 or published_spread_at is None:
        fail('no fully published scenario now separates the two cap readings')

    if max_spread <= 0 or spread_at is None:
        fail('no scenario now separates the two cap readings — the page’s central finding '
             'is the size of that separation and there would be nothing to publish')

    # ---- THE TIER CONTRAST, computed. The most useful sentence this page can produce.
    # The argument it answers -- "parents should pay more, they are the ones using the
    # schools" -- treats parents as one group. The same three athletes are two completely
    # different bills depending on which tier the family is in, and both are true at once.
    # Taken from the most recent year in which BOTH tiers are published, because FY2027
    # publishes no reduced rate at all and a contrast drawn across two years would not be
    # like for like (rule 6).
    contrast = None
    for y in years:
        t = y['levels']['HS']['tiers']
        if not (t['full']['available'] and t['reduced']['available']):
            continue
        pick = lambda tier, ch, sp: next(
            g for g in t[tier]['grid'] if g['children'] == ch and g['sports'] == sp)
        ch, sp = 3, 1
        full, red = pick('full', ch, sp), pick('reduced', ch, sp)
        contrast = dict(
            fy=y['fy'], level='HS', children=ch, sports=sp,
            full=full['per_year'], reduced=red['per_year'],
            waived=0.0, flat=t['reduced']['flat'],
            ratio=round(full['per_year'] / red['per_year'], 2) if red['per_year'] else None,
            full_published=full['fully_published'],
            source=t['reduced']['source'], source_ref=t['reduced']['source_ref'])
        break
    if contrast is None:
        fail('no year publishes both a full and a reduced athletic fee — the page states '
             'the contrast between the two tiers as its most concrete finding and there '
             'would be nothing to state it from')

    # ---- THE HOUSEHOLD TABLE. The page. Everything above is one row of it. -------------
    register = reg(c)
    hh_bills = households(c, register, years)
    hh_standing = standing_charges(register, 2027)
    hh_default = dict(fy=2027, level='HS', children=2, sports=1, tier='full',
                      bus=True, activities=True, parking=False)
    dk = hh_key(hh_default['fy'], hh_default['level'], hh_default['children'],
                hh_default['sports'], hh_default['tier'], hh_default['bus'],
                hh_default['activities'], hh_default['parking'])
    if dk not in hh_bills:
        fail(f'the household this page opens with ({dk}) was not priced — the table is the '
             'page and it would render empty')
    # The lead sentence is computed, never typed (rule 2). It is the bill for the household
    # in `hh_default`, which is the one the page opens on.
    lead = hh_bills[dk]
    if lead['floor_carried'] <= 0:
        fail('the household this page opens with now totals nothing — a lookup that matched '
             'nothing looks exactly like a family that pays nothing')
    unpriced_named = len([r for r in hh_standing if r['band'] == UNPRICED])

    unpriced_rows = unpriced(c)
    not_published = [u for u in unpriced_rows if u['status'] == 'not_published']

    gaps = {g['what']: g for g in q(c, 'SELECT side, what, why FROM money_gaps')}
    missing = [k for k in GAP_KEYS if k not in gaps]
    if missing:
        fail('money_gaps no longer carries: ' + '; '.join(missing) +
             ' — rule 7c says a limit this page hits is registered there, and a gap quoted '
             'by key that has been renamed renders as an empty box')

    def split(g):
        w = g['why']
        i = w.find('— closes:')
        return dict(side=g['side'], what=g['what'],
                    why=(w[:i].strip() if i >= 0 else w.strip()),
                    closes=(w[i + len('— closes:'):].strip() if i >= 0 else None))

    with open(REPORTS, encoding='utf-8') as fh:
        by_id = {r['id']: r for r in json.load(fh)['reports']}
    related = []
    for rid, why in RELATED:
        r = by_id.get(rid)
        if r is None:
            fail(f'reports.json no longer carries {rid}, which this page cites')
        related.append(dict(id=rid, title=r['title'], why=why, words=r['words'],
                            updated=r['updated'], url=r['markdown']['url'],
                            pdf=(r.get('pdf') or {}).get('url')))

    return dict(
        generated_by='scripts/build_what_families_pay.py',
        source='sources/data/lunenburg.db — athletic_fee_schedule, rate_register, '
               f'money_gaps; {FAQ_REL}; {MINUTES}/',
        seasons=SEASONS, max_children=MAX_CHILDREN, max_sports=MAX_SPORTS,
        default=dict(fy=2027, level='HS', children=2, sports=1, tier='full', bus=True),
        tiers=['full', 'reduced', 'waived'],
        schedule=[r for r in rows],
        caps=caps,
        cap_stated=[x['fy'] for x in stated],
        cap_unstated=[x['fy'] for x in unstated],
        ladder_exhibit=dict(
            fy=2027, level='HS', cap=cap27['amount'], seasons=1,
            published_steps=lad27['stops_after'], ratio=lad27['ratio'],
            ratio_pct=money((1 - lad27['ratio']) * 100), flat_rate=money(flat_rate),
            rows=ladder_exhibit, reaches_cap=False,
            rule='the published rates are 400, 400 x 0.75 and 400 x 0.75^2, to the cent — '
                 'the 25% sibling discount the School Committee voted for FY2026, '
                 'compounding down the ladder',
            assumption_rule='the same 25% keeps compounding past the third child',
            assumption_flat='the discount stops descending and every further child pays '
                            'the third-child rate — the more expensive of the two'),
        years=years,
        max_spread=max_spread, max_spread_at=spread_at,
        published_spread=published_spread, published_spread_at=published_spread_at,
        season_cap_binds_anywhere=any(
            t['season_cap_ever_binds'] for y in years for lv in ('HS', 'MS')
            for t in y['levels'][lv]['tiers'].values()),
        fourth_child=dict(
            fy=2027, level='HS', published_steps=lad27['stops_after'],
            by_rule=money(lad27['rates'][0] * lad27['ratio'] ** 3),
            flat=money(flat_rate),
            uncomputable=hs27['tiers']['full']['uncomputable'],
            inferred=hs27['tiers']['full']['inferred']),
        tier_contrast=contrast,
        household=dict(
            default=hh_default,
            options=dict(fy=YEARS, level=HH_LEVELS, children=HH_CHILDREN,
                         sports=HH_SPORTS, tier=HH_TIERS),
            bands=[PRICED, CARRIED, UNPRICED, NOCHARGE],
            band_meaning={
                PRICED: 'an amount a document states, for the year shown',
                CARRIED: 'charged, and the last rate set in public is from an earlier year',
                UNPRICED: 'charged, and no amount is published anywhere in this archive',
                NOCHARGE: 'a charge a family might expect and does not pay',
            },
            standing=hh_standing,
            charge_defs=DEFS,
            bills=hh_bills,
            lead=dict(key=dk, **{k: v for k, v in lead.items() if k != 'rows'},
                      rows=lead['rows']),
            unpriced_named=unpriced_named,
        ),
        unpriced=unpriced_rows,
        unpriced_count=len(not_published),
        # The portal fees on their own, because they are the ones a FAMILY meets: the
        # district sells them and publishes no amount for any of them. The other
        # unpublished rates in the register are a contract COLA and a facilities hire
        # schedule, which are not a household bill.
        unpriced_portal=len([u for u in not_published if u['category'] == 'other_fee']),
        faq=faq_rule(),
        said=said(),
        search_note=SEARCH_NOTE,
        coverage=coverage(),
        conclusions=the_conclusions(rows, register, lad27,
                                   money((1 - lad27['ratio']) * 100), contrast,
                                   hh_bills, hh_default, unpriced_named),
        gaps=[split(gaps[k]) for k in GAP_KEYS],
        related=related,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {rel} is not what the archive now produces. '
                  'Run scripts/build_what_families_pay.py.')
            return 1
        print(f'ok — {rel} reproduces from the archive')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    lx = d['ladder_exhibit']
    print(f'wrote {rel}')
    hh = d['household']
    L, defs = hh['lead'], hh['charge_defs']
    hd = hh['default']
    print(f"  THE HOUSEHOLD THIS PAGE OPENS ON — FY{hd['fy']}, {hd['children']} children at "
          f"the {hd['level']}, {hd['sports']} season each, riding the bus, in a club:")
    for r in L['rows']:
        amt = 'not published' if r['amount'] is None else f"{r['amount']:>10,.2f}"
        print(f"      {defs[r['id']]['label']:<24} {r['band']:<9} {amt}")
    print(f"      {'':<24} {'floor':<9} {L['floor']:>10,.2f}   published amounts only")
    print(f"      {'':<24} {'TOTAL':<9} {L['floor_carried']:>10,.2f}   with rates last set "
          f"in public but not restated")
    print(f"  and {hh['unpriced_named']} further named charges nobody publishes an amount "
          f"for, each with the document that would price it")
    print(f"  households priced: {len(hh['bills'])}")
    print(f"  cap period stated for FY{d['cap_stated']}, NOT stated for FY{d['cap_unstated']}")
    last = lx['rows'][-1]
    print(f"  {last['children']} children, one sport each, one season: "
          f"{last['cumulative_by_rule']:,.2f} if the {lx['ratio_pct']:.0f}% keeps "
          f"compounding, {last['cumulative_flat']:,.2f} if it stops — against a cap of "
          f"{lx['cap']:,.0f}. Neither reaches it.")
    print(f"  widest gap, every rate published: {d['published_spread']:,.0f} "
          f"(FY{d['published_spread_at']['fy']}, {d['published_spread_at']['children']} "
          f"children x {d['published_spread_at']['sports']} sports)")
    print(f"  widest gap including inferred rungs: {d['max_spread']:,.0f} "
          f"(FY{d['max_spread_at']['fy']}, {d['max_spread_at']['children']} children x "
          f"{d['max_spread_at']['sports']} sports)")
    print(f"  a per-season cap binds in any modelled scenario: "
          f"{d['season_cap_binds_anywhere']}")
    ct = d['tier_contrast']
    print(f"  FY{ct['fy']} HS, {ct['children']} children one sport each: "
          f"{ct['full']:,.2f} at the full fee against {ct['reduced']:,.2f} at the reduced "
          f"fee — {ct['ratio']:.0f}x")
    print(f"  named fees with no published amount: {d['unpriced_count']}, of which "
          f"{d['unpriced_portal']} are fees the district's own portal sells")
    return 0


if __name__ == '__main__':
    sys.exit(main())
