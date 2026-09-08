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
         why='Said in the room where the athletic fees were voted, and it is the point this '
             'page is built to test: athletics is the fee everybody argues about and it is '
             'not the only one a family pays. The $450 is a resident’s own arithmetic on a '
             'list of activities, at the same meeting where the activity fee was discussed '
             'and NOT voted — which is why this archive holds no activity fee schedule to '
             'check it against.'),
    dict(key='fortheyear',
         board='finance-committee', date='2025-03-20', doc='7010', kind='minutes',
         quote='The fee for 1 child is $180 and the family cap is $270 for the year.',
         who='the Finance Committee, on the bus fee set eight days earlier',
         why='The same district, the same budget cycle, a family cap — and the period '
             'stated in so many words. Four weeks before this, the athletic cap was voted '
             'with no period at all. That does not establish what the athletic cap means. '
             'It does establish that stating the period is something the town does when it '
             'has one in mind, so the omission is not a convention of minute-taking.'),
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
    'every build. No count of documents searched is published: the meeting archive was '
    'being enlarged and re-extracted while this page was written, so a coverage figure '
    'would have been stale within the hour. Nothing here claims that nobody else said '
    'anything — only that these people said these words, in these documents.')


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
