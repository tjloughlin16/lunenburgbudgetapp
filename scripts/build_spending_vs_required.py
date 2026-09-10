#!/usr/bin/env python3
"""What the town spends against the minimum the state requires — 33 years of it.

THE ONE MEASURE MASSACHUSETTS ACTUALLY ENFORCES. Chapter 70 sets a required net school
spending figure for every district, and a town that falls below it is out of compliance.
Everything else on this site is a budget the town chose; this is the floor underneath.

WHAT THE SERIES SHOWS, and it is not the story anybody tells about Lunenburg: the town
spent at the state median as recently as FY2018 -- 1.2978 against a median of 1.2978,
rank 181 of 361 -- and has fallen away since, to 1.1598 and rank 238 of 362 in FY2024.
That is the worst position since FY2005. The usual framing is that Lunenburg has always
been a low spender. Against this measure it was not.

RULE 1 IS THE WHOLE DIFFICULTY, and the data hands us the answer rather than hiding it:
`nss_stage` says ACTUAL for FY1994-FY2024 and BUDGETED for FY2025-FY2026. Those are two
stages of one quantity. A budgeted ratio and an actual ratio may not be differenced, and
a trend line drawn through both is a trend through a change of instrument. So the two are
carried in separate arrays, labelled, and the generator refuses to emit a single combined
series at all -- there is no field here that a caller could accidentally treat as one.

WHY THE RANK MATTERS MORE THAN THE RATIO. The ratio moves when the REQUIREMENT moves, and
the requirement is recomputed every year from enrollment and municipal wealth. The rank
against every other district in the same year removes that: it asks where Lunenburg sits
among districts all facing the same formula in the same year.

    python3 scripts/build_spending_vs_required.py
    python3 scripts/build_spending_vs_required.py --check
"""
import argparse
import collections
import csv
import json
import re
import os
import sqlite3
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'spending-vs-required.json')
LEA = '01620000'
MIN_YEARS = 25
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MINUTES = 'sources/meetings/text'
DOC_KEY = 'state-dese/dese-ch70-district-profile.xlsx'

# WHAT THE TOWN SAID, rule 15a. Every quote is re-read out of the extracted minutes on
# this run and a miss stops the build: a quote is a claim about a document, and rule 13
# says quote the source rather than your rendering of it.
#
# THE PATTERN ACROSS THEM IS THE FINDING, and it is a negative one. This measure comes up
# in Lunenburg meetings almost entirely inside ANOTHER district's budget presentation --
# Monty Tech's business manager, presenting Monty Tech's figures to the Finance
# Committee. Nobody in these documents states Lunenburg Public Schools' own position
# against the required minimum, in any year.
QUOTES = [
    dict(key='average', board='finance-committee', date='2024-03-20', kind='minutes',
         doc='6481',
         quote='Evan Watters reiterates that the state is spending an average of 126% '
               'and asks how that works. Tammy Crockett states each school gets a '
               'different net school spending number. It changes from district to '
               'district and is a balancing act of what each town can afford. If you go '
               'below 95% you won’t get the chapter 70 increases.',
         why='THE QUESTION THIS PAGE ANSWERS, ASKED IN PUBLIC AND LEFT OPEN. A Finance '
             'Committee member asks where the state sits on exactly this ratio; the '
             'answer given is that it differs by district. It was asked during MONTY '
             'TECH’s budget presentation, by its business manager, and no figure '
             'for Lunenburg Public Schools was put beside it. The 126% is a statewide '
             'AVERAGE as stated; every state figure on this page is a MEDIAN, which is '
             'a different statistic and is not compared to it here.'),
    dict(key='definition', board='finance-committee', date='2024-03-20', kind='minutes',
         doc='6481',
         quote='This is the minimum spending every school district must spend not '
               'including debt services, capital transportation, meals.',
         why='WHAT NET SCHOOL SPENDING IS, said to the Finance Committee in the town’s '
             'own record. The exclusions are the reason no line in the town’s budget '
             'or the district’s book equals the figure on this page — which is '
             'registered as a gap rather than reconciled here. The dollar amount in the '
             'same passage is MONTY TECH’s requirement, not Lunenburg’s.'),
    dict(key='discretionary', board='finance-committee', date='2025-03-06',
         kind='minutes', doc='7008',
         quote='Tammy Crockett conﬁrms that the above net school spending and '
               'capital are not mandated.',
         why='THE WHOLE SUBJECT OF THIS PAGE IN ONE SENTENCE, said about another '
             'district: the amount ABOVE the required minimum is the part nobody has to '
             'spend. Every district’s position in the ranking is made of that part.'),
    dict(key='bottom', board='school-committee', date='2024-01-24', kind='minutes',
         doc='6375',
         quote='According to Massachusetts State reports Lunenburg per pupil expenditure '
               'is listed 361 out of 401 districts in Massachusetts. This means that '
               "we're in the top 20% for school performance while being in the "
               "bottom 10% for spending",
         why='THE STORY THE TOWN TELLS ABOUT ITSELF, in public comment during the FY2025 '
             'cuts. It is about PER PUPIL spending, which is a different measure from '
             'this one and is on /what-other-districts-spend. Against the measure the '
             'state enforces, the position is nothing like the bottom tenth — which '
             'is the correction this page exists to make, in the town’s favour and '
             'not against it. Neither figure in the quote is checkable here: this '
             'archive holds no statewide MCAS distribution, and the 401 denominator is '
             'not the one DESE publishes for district finance.'),
]

# The terms searched, with their denominators. A grep that finds nothing prints nothing,
# and nothing reads as nobody said it.
SEARCHED = ['net school spending', 'required minimum', 'foundation budget',
            'per pupil expenditure', 'underfunded', 'levy limit', 'override']

# The rows of the gap register this page rests on, cited BY KEY. The register outranks the
# page (rule 7c): if a `what` here is not in money-gaps.csv the build stops rather than
# rendering a limit that no records request will ever ask about.
GAP_KEYS = [
    'What Lunenburg’s net school spending actually was in the two most recent years',
    'How the district’s own accounts add up to the net school spending DESE reports',
    'Whether spending less per pupil is a choice or a constraint',
]


def fail(msg):
    raise SystemExit(msg + ' Nothing written.')


def and_list(items):
    """`a, b and c`, built rather than typed, because the number of items is data."""
    items = list(items)
    if len(items) == 1:
        return items[0]
    return '%s and %s' % (', '.join(items[:-1]), items[-1])


def ratio_text(x):
    """A spending-to-requirement ratio, at the four decimal places DESE publishes it to.
    Not a percentage: the page, the table and the town all say `times the requirement`,
    and 1.2978 against a median of 1.2978 is a statement four decimals make and two
    destroy."""
    return '%.4f' % float(x)


def document():
    """Rule 12: the figures travel with the document, its address and its sha256."""
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row['key'] == DOC_KEY:
                return {
                    'path': 'sources/' + row['key'], 'sha256': row['sha256'],
                    'bytes': int(row['bytes']), 'url': row['upstream'],
                    'docs_url': '/docs/' + row['key'],
                    'filename': row['key'].split('/')[-1],
                    'publisher': 'Massachusetts Department of Elementary and Secondary '
                                 'Education',
                    'table': 'dese_ch70_formula and dese_ch70_statewide',
                    'note': 'Required net school spending is the floor Chapter 70 sets. '
                            'A district below it is out of compliance. This is the one '
                            'spending measure the state enforces rather than observes.',
                }
    fail('%s is not in the archive manifest. A figure without its document is not '
         'publishable.' % DOC_KEY)


def said_in_meetings():
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here -- a quote on this page is attributed to a document '
                 'that is not in the archive.' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s -- quote the source, '
                 'never your rendering of it.' % (spec['board'], spec['date'], rel))
        kind = 'Minutes' if spec['kind'] == 'minutes' else 'Agenda'
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], kind=kind,
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/%s/_%s%s%s-%s'
                 % (kind, spec['date'][5:7], spec['date'][8:10], spec['date'][:4],
                    spec['doc'])))
    return out


def searched():
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here -- a search of nothing is not a '
             'search.')
    readable = []
    for r in csv.DictReader(open(idx, encoding='utf-8')):
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
    if not readable:
        fail('no meeting document is readable -- refusing to publish a count of what '
             'nobody said.')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies if re.search(re.escape(t), b, re.I)))
             for t in SEARCHED]

    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here -- the searchable share '
             'cannot be typed.')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile -- refusing to publish a coverage '
             'figure that does not add up.')
    return terms, dict(held=tally['held'], searchable=tally['searchable'],
                       unsearchable=tally['unsearchable'],
                       image_scan=tally['image_scan'],
                       searchable_share=round(tally['searchable'] / tally['held'], 4))


def gaps():
    """The register, read. A limit stated only in this page's prose is invisible."""
    reg = {row['what']: row for row in csv.DictReader(open(GAPS, encoding='utf-8'))}
    out = []
    for k in GAP_KEYS:
        if k not in reg:
            fail('the gap %r is not in money-gaps.csv. The register outranks the page.' % k)
        why = reg[k]['why']
        if '— closes:' not in why:
            fail('the gap %r names no document that would close it. A gap with no remedy '
                 'is a grievance, not a records request.' % k)
        body, closes = why.split('— closes:', 1)
        out.append(dict(side=reg[k]['side'], what=k, why=body.strip(),
                        closes=closes.strip()))
    return out


def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)

    rows = db.execute("""
        SELECT fy, nss_stage, required_nss, net_school_spending, nss_pct_of_required,
               reconciles
        FROM dese_ch70_formula WHERE lea=? AND level='district'
          AND net_school_spending IS NOT NULL
        ORDER BY fy""", (LEA,)).fetchall()
    if len(rows) < MIN_YEARS:
        raise SystemExit('only %d years of net school spending; expected at least %d. '
                         'Nothing written.' % (len(rows), MIN_YEARS))

    stages = {r[1] for r in rows}
    if not stages <= {'actual', 'budgeted'}:
        raise SystemExit('unexpected nss_stage values %r. This file splits on stage and '
                         'refuses to guess where a new one belongs. Nothing written.'
                         % sorted(stages))
    unreconciled = [r[0] for r in rows if r[5] != 'yes']
    if unreconciled:
        raise SystemExit('these years do not reconcile: %r. Nothing written.' % unreconciled)

    # `lunenburg_rank_of_districts` is a STRING like "103 of 368", not a number. It is a
    # rendering of two facts stuck together -- rule 13's shape, in a column -- so it is
    # split back apart here rather than being formatted or compared as text.
    def _rank(v):
        m = re.match(r'\s*(\d+)\s+of\s+(\d+)', str(v or ''))
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)

    state = {(fy): (med, lun, rank, n, basis, p25, p75)
             for fy, basis, med, lun, rank, n, p25, p75 in db.execute(
        """SELECT fy, basis, median, lunenburg, lunenburg_rank_of_districts, districts,
                  p25, p75
           FROM dese_ch70_statewide WHERE measure LIKE '%net school spending%'""")}
    if not state:
        raise SystemExit('the statewide comparison matched nothing. A join that matches '
                         'nothing looks exactly like a district nobody ranks. '
                         'Nothing written.')

    def pack(stage):
        out = []
        for fy, st, req, nss, pct, _ in rows:
            if st != stage:
                continue
            s = state.get(fy)
            rk, of = _rank(s[2]) if s else (None, None)
            out.append({
                'fy': fy, 'required': round(req), 'spent': round(nss),
                'ratio': round(pct, 4),
                'above_required': round(nss - req),
                'state_median': round(s[0], 4) if s else None,
                # THE MIDDLE HALF. Carried because "below the median" and "in the bottom
                # quarter" are different statements and this project publishes a page that
                # makes the second one about a DIFFERENT measure. Without the quartiles a
                # reader has no way to tell which of the two this series supports.
                'p25': round(s[5], 4) if s and s[5] is not None else None,
                'p75': round(s[6], 4) if s and s[6] is not None else None,
                'rank': rk,
                'districts': of or (s[3] if s else None),
                # THE COUNTERFACTUAL, per year and labelled. What the town would have
                # spent at the state's median ratio. Arithmetic on a published median,
                # not a claim that anybody could or should have spent it.
                'at_state_median': round(req * s[0]) if s else None,
                'short_of_median': round(req * s[0] - nss) if s else None,
            })
        return out

    actual = pack('actual')
    budgeted = pack('budgeted')
    if not actual:
        raise SystemExit('no ACTUAL years survived the split. Nothing written.')

    ranked = [a for a in actual if a['rank']]
    best = min(ranked, key=lambda a: a['rank'])
    worst_recent = min(ranked, key=lambda a: -a['fy'])
    at_or_above = [a for a in ranked if a['state_median'] and a['ratio'] >= a['state_median']]

    terms, minutes = searched()

    # ---- THE CONCLUSIONS -------------------------------------------------------------
    # Six quantities the payload does not otherwise carry, computed here beside the
    # series so that no figure in a sentence is typed (rule 2):
    #   * the REFERENCE year the recent fall is measured from -- the most recent year in
    #     which Lunenburg landed on the state median exactly, which is where the position
    #     turned. Found rather than named, so it moves when DESE republishes;
    #   * how far the requirement and the spending each moved from that year, in dollars
    #     and as percentages. These two are the whole of the second conclusion;
    #   * the last year before the latest one that ranked as low, so "weakest since" is
    #     computed rather than remembered;
    #   * the narrowest year, and the years below the state's first quartile.
    exact = [r for r in ranked
             if r['state_median'] and abs(r['ratio'] - r['state_median']) < 5e-5]
    if not exact:
        raise SystemExit('no year in which Lunenburg landed on the state median. The '
                         'second conclusion measures the recent fall from that year, and '
                         'it cannot be named if it does not exist. Nothing written.')
    base = exact[-1]
    latest = ranked[-1]
    span_years = latest['fy'] - base['fy']
    req_growth_pct = 100 * (latest['required'] / base['required'] - 1)
    spent_growth_pct = 100 * (latest['spent'] / base['spent'] - 1)
    worse = [r for r in ranked[:-1] if r['rank'] >= latest['rank']]
    if not worse:
        raise SystemExit('no earlier year ranks as low as the latest one, so there is no '
                         '"weakest since" to state. Nothing written.')
    worst_since = worse[-1]
    narrowest = min(ranked, key=lambda r: r['ratio'])
    below_p25 = [r for r in ranked if r['p25'] and r['ratio'] < r['p25']]
    if not below_p25:
        raise SystemExit('no year below the state first quartile. The first conclusion '
                         'counts them. Nothing written.')
    median_gap_pct = 100 * latest['short_of_median'] / latest['spent']

    conclusions = emit('what-the-state-requires-us-to-spend', [
            # ORDER IS THE ARGUMENT. This led with '14 of 31 years at or above the
            # state median', which is true, backward-looking and the least useful of
            # the three. TJ: "this stat is NOT the important one for this data". The
            # finding a reader needs first is WHY the position moved -- the requirement
            # rose 25.2% while spending rose 11.9%, so the slide is the bar moving and
            # not the town spending less. Then what closing it would cost. The history
            # comes third: useful context, not the headline.
        conclusion(
            id='the-requirement-moved-faster-than-the-spending',
            bearing='sizes',
            claim='Rise in the state minimum since FY2018, against a rise in spending of half that',
            so_what='Lunenburg’s slide down the state ranking is mostly the bar moving, not the town spending less.',
            lede='Lunenburg’s slide down the state ranking since %s is mostly the bar '
                  'rising: the requirement went up %s over those years while what the '
                  'town spent went up %s.'
                  % (C.fy(base['fy']), C.pct(req_growth_pct), C.pct(spent_growth_pct)),
            detail='Required net school spending rose %s and what the town spent rose %s '
                   '— spending ends the period higher than it started and rose more '
                   'slowly than the figure it is measured against. The rank went from %s '
                   'of %s districts in %s to %s of %s in %s, the weakest position since '
                   '%s. The requirement is recomputed every year from enrollment and '
                   'municipal wealth, so a district can spend more each year and still '
                   'fall. And a fall that took %s years is a different problem, with '
                   'different remedies, from a condition that has held since the series '
                   'began.'
                   % (C.usd(latest['required'] - base['required']),
                      C.usd(latest['spent'] - base['spent']),
                      C.num(base['rank']), C.num(base['districts']), C.fy(base['fy']),
                      C.num(latest['rank']), C.num(latest['districts']),
                      C.fy(latest['fy']), C.fy(worst_since['fy']), C.num(span_years)),
            figures=dict(
                base_fy=figure(base['fy'], C.fy(base['fy'])),
                required_pct=figure(req_growth_pct, C.pct(req_growth_pct)),
                spent_pct=figure(spent_growth_pct, C.pct(spent_growth_pct)),
                required_change=figure(latest['required'] - base['required'],
                                       C.usd(latest['required'] - base['required'])),
                spent_change=figure(latest['spent'] - base['spent'],
                                    C.usd(latest['spent'] - base['spent'])),
                base_rank=figure(base['rank'], C.num(base['rank'])),
                base_districts=figure(base['districts'], C.num(base['districts'])),
                rank=figure(latest['rank'], C.num(latest['rank'])),
                districts=figure(latest['districts'], C.num(latest['districts'])),
                fy=figure(latest['fy'], C.fy(latest['fy'])),
                worst_since_fy=figure(worst_since['fy'], C.fy(worst_since['fy'])),
                span=figure(span_years, C.num(span_years))),
            figure='required_pct',
            kind='measured',
            basis='The same ACTUAL series, differenced between %s and %s, against '
                  'DESE’s statewide rank for Lunenburg in each of those two years. Both '
                  'ends are the same stage of the same quantity, which is the only reason '
                  'the difference can be taken at all.'
                  % (C.fy(base['fy']), C.fy(latest['fy'])),
            not_shown='That this measures the recent budget reductions. The most recent '
                      'ACTUAL year here is %s; the years the town argued about are '
                      'published so far only as BUDGETED figures, and a budgeted ratio '
                      'and a spent one are two stages of one quantity. Nor does it show '
                      'WHY the requirement rose — enrollment and municipal wealth both '
                      'feed it and this series cannot separate them.' % C.fy(latest['fy']),
            see=[('/why-we-only-get-minimum-aid',
                  'why the requirement itself keeps rising')],
        ),
        conclusion(
            id='what-the-median-would-have-cost',
            bearing='lever',
            claim='More than Lunenburg spent, to match the middle district in the state',
            so_what='A subtraction on a published median. Nobody has proposed it and nothing is costed against it.',
            lede='Spending like the middle district in Massachusetts would have meant '
                  '%s more than Lunenburg spent in %s — %s more, on a state minimum '
                  'of %s.'
                  % (C.fy(latest['fy']), C.usd(latest['short_of_median']),
                     C.pct(median_gap_pct), C.usd(latest['required'])),
            detail='The median district spent %s times its required net school spending '
                   'that year; Lunenburg spent %s. Applying the median ratio to '
                   'Lunenburg’s own requirement gives %s against the %s it actually '
                   'spent. That is a subtraction on a published median and nothing more: '
                   'nobody has proposed it and no programme is costed against it. It is '
                   'here because a rank is hard to weigh at a meeting and a dollar amount '
                   'is not.'
                   % (ratio_text(latest['state_median']), ratio_text(latest['ratio']),
                      C.usd(latest['at_state_median']), C.usd(latest['spent'])),
            figures=dict(
                fy=figure(latest['fy'], C.fy(latest['fy'])),
                gap=figure(latest['short_of_median'], C.usd(latest['short_of_median'])),
                gap_pct=figure(median_gap_pct, C.pct(median_gap_pct)),
                required=figure(latest['required'], C.usd(latest['required'])),
                state_median=figure(latest['state_median'],
                                    ratio_text(latest['state_median'])),
                ratio=figure(latest['ratio'], ratio_text(latest['ratio'])),
                at_state_median=figure(latest['at_state_median'],
                                       C.usd(latest['at_state_median'])),
                spent=figure(latest['spent'], C.usd(latest['spent']))),
            figure='gap',
            kind='measured',
            basis='DESE’s statewide distribution of net school spending as a share of the '
                  'requirement — the median column for %s — applied to Lunenburg’s own '
                  'required net school spending in the same year.' % C.fy(latest['fy']),
            not_shown='What the money would have bought, and whether the median is a '
                      'target at all. Half of Massachusetts districts spend below it, it '
                      'moves every year with what every other town decides, and no '
                      'programme anywhere in this archive is costed against this figure.',
            see=[('/what-other-districts-spend',
                  'the per-pupil comparison, which is a different measure')],
        ),
        conclusion(
            id='the-enforced-floor-has-never-been-missed',
            bearing='sizes',
            claim='Years Lunenburg spent at or above what the middle district in the state spent',
            so_what='Massachusetts sets a minimum every town must spend on its schools. Lunenburg has never missed it.',
            lede='Massachusetts sets a minimum every town must spend on its own '
                  'schools. Lunenburg has met it in all %s years measured, and in %s of '
                  'those years spent at or above what the middle district in the state '
                  'spent.'
                  % (C.num(len(ranked)), C.num(len(at_or_above))),
            detail='A district spending below its required net school spending is out of '
                   'compliance. Lunenburg’s narrowest year was %s, at %s times the '
                   'requirement. The story the town tells about itself is that it has '
                   'always been a low spender, and against the measure the state enforces '
                   'it has not been: it landed exactly on the state median in %s — %s '
                   'against a median of %s — and has been below the state’s first '
                   'quartile in %s of those years, %s. That is a real thing to know '
                   'before any argument about what the schools are owed.'
                   % (C.fy(narrowest['fy']), ratio_text(narrowest['ratio']),
                      C.fy(base['fy']), ratio_text(base['ratio']),
                      ratio_text(base['state_median']), C.num(len(below_p25)),
                      and_list([C.fy(r['fy']) for r in below_p25])),
            figures=dict(
                years=figure(len(ranked), C.num(len(ranked))),
                at_or_above=figure(len(at_or_above), C.num(len(at_or_above)),
                                       'of %s years measured' % C.num(len(ranked))),
                narrowest_fy=figure(narrowest['fy'], C.fy(narrowest['fy'])),
                narrowest_ratio=figure(narrowest['ratio'],
                                       ratio_text(narrowest['ratio'])),
                median_fy=figure(base['fy'], C.fy(base['fy'])),
                median_ratio=figure(base['ratio'], ratio_text(base['ratio'])),
                state_median=figure(base['state_median'],
                                    ratio_text(base['state_median'])),
                below_p25=figure(len(below_p25), C.num(len(below_p25))),
                **{'below_p25_%d' % r['fy']: figure(r['fy'], C.fy(r['fy']))
                   for r in below_p25}),
            figure='at_or_above',
            kind='measured',
            basis='DESE’s Chapter 70 district profile: required net school spending '
                  'against net school spending as reported, ACTUAL stage only, %s, with '
                  'the statewide median and quartiles for each of those years. The two '
                  'most recent years DESE publishes are BUDGETED and are counted nowhere '
                  'in this.' % C.fyspan(ranked[0]['fy'], ranked[-1]['fy']),
            not_shown='Whether meeting the floor was a choice or a ceiling. The levy '
                      'limit, two failed overrides, the district’s request and Town '
                      'Meeting’s vote all resolve into this single number, and nothing '
                      'here separates them.',
            see=[('/what-other-districts-spend',
                  'what districts spend for each pupil, which is a different measure'),
                 ('/overrides', 'the overrides the town has voted on')],
        ),
    ])

    return {
        'conclusions': conclusions,
        'about': 'Lunenburg’s net school spending against the minimum Chapter 70 requires, '
                 'and against every other district in the same year.',
        'source': document(),
        'said': said_in_meetings(),
        'searched': terms,
        'minutes': minutes,
        'gaps': gaps(),
        'stage_warning': 'nss_stage is ACTUAL for FY%d–FY%d and BUDGETED for FY%d–FY%d. '
                         'These are two stages of one quantity and are never differenced, '
                         'never averaged, and never drawn as one line.'
                         % (actual[0]['fy'], actual[-1]['fy'],
                            budgeted[0]['fy'], budgeted[-1]['fy'])
                         if budgeted else 'All years are the ACTUAL stage.',
        'actual': actual,
        'budgeted': budgeted,
        'best_rank': best,
        'latest_actual': actual[-1],
        'years_at_or_above_median': len(at_or_above),
        'years_measured': len(ranked),
        'not_established': [
            'WHETHER THIS IS A CHOICE OR A CEILING. The levy limit, two failed overrides, '
            'the district’s request and Town Meeting’s vote all resolve into this one '
            'number, and nothing here separates them.',
            'WHAT THE MONEY WOULD HAVE BOUGHT. The gap to the median is arithmetic on a '
            'published median. It is not a costed programme and nobody has proposed it.',
            'THAT THE RATIO MEASURES EFFORT. It moves when the REQUIREMENT moves, and the '
            'requirement is recomputed each year from enrollment and municipal wealth. That '
            'is why the rank against other districts is carried beside it.',
        ],
        'closes': 'Nothing further is needed to measure this — DESE publishes it annually. '
                  'What is not published is WHY a district lands where it does, which is a '
                  'question about town meetings rather than about data.',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()
    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT)); return 1
        with open(OUT, encoding='utf-8') as fh:
            if json.load(fh) != data:
                print('STALE %s — run: python3 scripts/build_spending_vs_required.py'
                      % os.path.relpath(OUT, ROOT)); return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT)); return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True); fh.write('\n')
    b, l = data['best_rank'], data['latest_actual']
    print('%s: %d actual years, %d budgeted'
          % (os.path.relpath(OUT, ROOT), len(data['actual']), len(data['budgeted'])))
    print('  best rank  FY%d  %.4f vs median %.4f — rank %d of %d'
          % (b['fy'], b['ratio'], b['state_median'], b['rank'], b['districts']))
    print('  latest     FY%d  %.4f vs median %.4f — rank %d of %d'
          % (l['fy'], l['ratio'], l['state_median'], l['rank'], l['districts']))
    print('  at or above the median in %d of %d measured years'
          % (data['years_at_or_above_median'], data['years_measured']))
    print('  FY%d gap to the median ratio: $%s'
          % (l['fy'], format(l['short_of_median'], ',')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
