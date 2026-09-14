#!/usr/bin/env python3
"""THE BUDGET FEED: everything budget-related across every board, on one page.

    python3 scripts/build_budget_feed.py            # write fy28/public/data/budget-feed.json
    python3 scripts/build_budget_feed.py --check    # fail if it no longer reproduces

TJ, 14 September 2026: "a single page that pulls all the meetings together across all
boards and data into a single page. this shows the budget calendar. it shows any recent
meeting that discussed school budget or any budget planning info. It shows upcoming
meetings about the budget... once budget season hits, this will be the hottest page of all
latest and greatest content. but now, it auto-captures anything that is budget related
too, in case the boards have discussed anything for budget planning, esp as it relates to
annual town meeting."

FOUR PARTS, EVERY ONE A FILTER OVER SOMETHING ANOTHER GENERATOR ALREADY HOLDS:

  1. UPCOMING -- the meeting feed's coming meetings, kept where the posted agenda's own
     text carries a budget marker (below). Any board. With the join links the agenda prints.
  2. THE CALENDAR, THIS CYCLE -- the stages of a budget year in order, each with the window
     measured off the three budget boards' past agendas (build_boards.py), and where today
     falls against it.
  3. RECENT DISCUSSION -- newest first, one entry per thing said: our minutes' topics that
     carry a budget tag (with the second in the video), budget items and transfers, votes
     whose motion carries a marker; and, for meetings we have no minutes of, the agendas
     and official minutes whose text carries a marker.
  4. DOCUMENTS AND NOTICES -- the district budget page and the town's finance pages when
     they change, and feed items whose title carries a marker.

A MARKER IS A WORD, AND THAT IS ALL IT IS. "Budget" on an agenda says the board scheduled
the subject, not what it decided; a topic tagged `override` in our minutes says the model
that wrote them heard the subject discussed. The page says so. Nothing here is written by
a model at build time.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from budget_cycles import cycle_for, span as cycle_span   # noqa: E402
DATA = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT = os.path.join(DATA, 'budget-feed.json')
RECORDED = os.path.join(DATA, 'recording-minutes.json')
FEED = os.path.join(DATA, 'meeting-feed.json')
NOTICES = os.path.join(DATA, 'notices.json')
BOARDS = os.path.join(DATA, 'boards.json')
WHATS_NEW = os.path.join(DATA, 'whats-new.json')
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')
FEED_EVENTS = os.path.join(ROOT, 'sources', 'data', 'feed-watch-events.csv')
DOC_EVENTS = os.path.join(ROOT, 'sources', 'data', 'document-watch-events.csv')
BALLOTS = os.path.join(ROOT, 'sources', 'data', 'ballot-questions.csv')
EPISODES = os.path.join(ROOT, 'sources', 'data', 'budget-episodes.csv')
MODEL = os.path.join(DATA, 'model.json')
STATE = os.path.join(ROOT, 'sources', 'data', 'budget-state')

RECENT_DAYS = 90          # how far back "recent" reaches
DOC_DAYS = 120

# WHAT COUNTS. TJ, 14 September 2026: "this isn't just about anything with money attached.
# its specifically about the overall budget. Things that will land in the annual town
# meeting warrant as a monied article. the omnibus budget. but ESPECIALLY the school
# budget... what are they discussing to prepare for the annual town meeting." So: the
# budget being built, the warrant, Town Meeting, an override, and the revenue that sizes the
# budget (state aid, the levy, free cash). NOT line-item transfers, grants, fees, a
# department's spending, a closeout -- money, but not the budget.
BUDGET_TAGS = {'budget', 'budget-fy27', 'budget-fy28', 'override', 'town-meeting', 'warrant-article',
               'free-cash', 'state-aid', 'chapter-70', 'tax-rate', 'capital'}
# The words that mark an agenda, a set of minutes, a vote or a notice as Town Meeting
# preparation. Generic money words -- transfer, revenue, closeout, fiscal year -- are not here.
MARKER = re.compile(r'\b(town\s+meeting|warrant|override|omnibus|proposed\s+budget|preliminary\s+budget|draft\s+budget|'
                    r'budget\s+(?:hearing|presentation|overview|update|review|discussion|workshop|vote|message|request|calendar|timeline|process|priorities)|'
                    r'(?:school|town|operating|capital|municipal)\s+budget|fy\s?2[78]\s+budget|budget\s+fy\s?2[78]|'
                    r'levy\s+(?:limit|cap)|free\s+cash|chapter\s*70|state\s+aid|cherry\s+sheet|capital\s+(?:plan|request|article)|'
                    r'debt\s+exclusion|stabilization\s+fund)', re.I)
# The stages of a budget year, in the order they come, with the marker each is measured
# from on the boards' calendars (build_boards.py) and which board leads it.
# Rule 8: the feed shows what a board decided, never who voted which way. Our minutes
# record roll calls by name; the feed keeps the tally and drops the names. An appointment
# is a person, not a budget decision, even when the motion names a budget committee.
APPOINTMENT = re.compile(r'^\s*(re-?)?appoint', re.I)
# Housekeeping that names the budget without deciding anything about it: passing over an
# item, tabling it, skipping it, opening a hearing. Our minutes flag only adjournment and
# the like as procedural, so the feed draws this line itself.
HOUSEKEEPING = re.compile(r'^\s*(pass over|skip|table|postpone|continue|enter|open|close|accept the minutes|approve the minutes|approve the agenda)\b', re.I)


def tally_only(outcome):
    if not outcome:
        return outcome
    o = re.sub(r'\s*\((?:roll call|by roll call)[^)]*\)', '', outcome, flags=re.I)
    o = re.sub(r'\s*\([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+[a-z]+)*\)', '', o)   # "(Emily)", "(Tom Gray appointed)" 
    return o.strip()


STAGES = [
    ('Budget presented and reviewed', 'budget-presentation', ['finance-committee', 'school-committee', 'select-board']),
    ('Budget hearing', 'budget-hearing', ['school-committee', 'finance-committee']),
    ('Budget vote', 'budget-vote', ['school-committee', 'select-board']),
    ('Override discussed', 'override', ['select-board', 'school-committee', 'finance-committee']),
    ('Warrant articles', 'warrant', ['finance-committee', 'select-board']),
    ('Town Meeting', 'town-meeting', ['select-board', 'finance-committee']),
    ('Warrant opens and closes', 'warrant-closes', ['select-board']),
    ('Citizens’ petitions', 'petition', ['select-board', 'finance-committee', 'school-committee']),
]
MONTHS = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']


def read_csv(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8'))) if os.path.exists(p) else []


def load(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def cycle_pos(text):
    """'Mar 15' -> a position in the July-June year, for comparing against today."""
    mon, day = text.split()
    return MONTHS.index(mon) * 31 + int(day)


def today_pos(as_of):
    d = dt.date.fromisoformat(as_of)
    return ((d.month - 6) % 12) * 31 + d.day


def agenda_text(slug, row):
    p = os.path.join(TEXT, slug, os.path.splitext(os.path.basename(row['path']))[0] + '.txt')
    return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''


def hits(text, n=4):
    """The distinct marker words a text carries, lower-cased, a few of them."""
    seen, out = set(), []
    for m in MARKER.finditer(text or ''):
        w = re.sub(r'\s+', ' ', m.group(0).lower())
        w = {'appropriated': 'appropriation', 'appropriations': 'appropriation'}.get(w, w)
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:n]


def fy_of_date(as_of):
    return cycle_for(as_of)['fy']


def cycle_start(as_of):
    return cycle_span(fy_of_date(as_of))[0] or ('%d-05-21' % (fy_of_date(as_of) - 2))


def norm_item(text):
    """A cut's identity across meetings: the words, lower-cased, without the filler."""
    t = re.sub(r'[^a-z0-9 ]+', ' ', (text or '').lower())
    t = re.sub(r'\b(the|a|an|of|for|and|to|position|positions|reduction|reduce|cut|eliminate|eliminated)\b', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def episodes_for(fy):
    """The episodes of a season -- the regular cycle and the special ones (a Special Town
    Meeting, a post-election cut list, new state aid) -- from sources/data/budget-episodes.csv.
    TJ, 14 September 2026: "the 418k was not a deficit... a spending plan. So your FY28
    should probably be FY28-governors-budget or something, and be presented that way."
    A season without a row gets one regular episode covering the whole cycle."""
    rows = [r for r in read_csv(EPISODES) if int(r['season_fy']) == fy]
    # the season the page is named for leads; its special episodes follow, latest first
    rows = [r for r in rows if r['kind'] == 'regular'] + sorted([r for r in rows if r['kind'] != 'regular'], key=lambda r: r['opens'] or '', reverse=True)
    return rows


def in_episode(ep, date, about_fy):
    """A statement belongs to an episode by its date window, and a statement that names a
    fiscal year belongs to an episode about that year."""
    if ep.get('about_fy') and about_fy and int(ep['about_fy']) != int(about_fy):
        return False
    if ep.get('opens') and date < ep['opens']:
        return False
    if ep.get('closes') and date > ep['closes']:
        return False
    return True


def budget_state(as_of, episode=None):
    """THE LATEST, and what changed. TJ: "School committee announced 10 cuts for a $2m
    deficit... the cuts named so far (keeping up with changes, for when the cut lists
    change weekly)."

    Reads every budget-state file (write_budget_state.py), newest first. For each scope
    (school, town) and kind (deficit, override, budget total, state aid, free cash), the
    LATEST statement that carried a figure wins and is shown with who said it, its status
    and its second in the video; the earlier ones are its history. Cuts are keyed by their
    words: the latest status of each named cut is the list "so far", and each meeting that
    added, restored or withdrew one is a line in the change log."""
    files = sorted(glob.glob(os.path.join(STATE, '*', '*.json')))
    docs = []
    cycle_start_ = cycle_start(as_of)
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        if cycle_start_ <= d['meeting_date'] <= as_of:
            docs.append(d)
    docs.sort(key=lambda d: d['meeting_date'])
    keep = (lambda date, fy: in_episode(episode, date, fy)) if episode else (lambda date, fy: True)
    # A cut belongs to the episode in which it was FIRST named; an episode that only restates
    # it -- the July talk of June's cuts -- does not list it again unless its status changed.
    first_named = {}
    for d0 in docs:
        for c0 in d0['state'].get('cuts') or []:
            first_named.setdefault((c0['scope'], norm_item(c0['item'])), d0['meeting_date'])
    latest, history = {}, collections.defaultdict(list)
    cuts, log = {}, []
    # WHO SAID IT RANKS THE FIGURE. A deficit the superintendent or business administrator
    # stated outranks a member's, which outranks a resident's at public comment: the
    # latest statement wins only among the highest rank that has spoken this season.
    RANK = [(r'superintendent|business administrator|town manager|finance director|accountant|assistant town manager', 3),
            (r'chair', 2), (r'member|committee', 1)]
    def rank(who):
        w = (who or '').lower()
        return next((n for rx, n in RANK if re.search(rx, w)), 0)
    def well_formed(amount):
        a = (amount or '').strip()
        # A dollar figure, or a count of millions: a bare percentage or a mangled number is not a budget figure.
        return bool(re.search(r'\$\s?\d{1,3}(,\d{3})+(\.\d+)?|\$\s?\d+(\.\d+)?\s?(million|m|k|thousand)\b|\b\d+(\.\d+)?\s?million\b', a, re.I))
    RESTORE = re.compile(r'\b(restor\w*|reinstat\w*|add(?:ed|ing)?\b|increas\w*|expand\w*|new position|hire|bring back|fund(?:ed|ing)? back|return)', re.I)
    for d in docs:
        page = '/meeting-minutes/%s/%s-%s' % (d['board_slug'], d['meeting_date'], d['video_id'])
        base = dict(board=d['board'], board_slug=d['board_slug'], date=d['meeting_date'], page=page)
        for st in d['state'].get('statements') or []:
            if st['kind'] == 'other' or not well_formed(st.get('amount_as_heard')):
                continue
            if not keep(d['meeting_date'], st.get('fiscal_year')):
                continue
            key = (st['scope'], st['kind'])
            row = dict(base, **st, video_url='%s&t=%ds' % (d['video_url'], st['t']), rank=rank(st.get('who')))
            history[key].append(row)
            if key not in latest or row['rank'] >= latest[key]['rank']:
                latest[key] = row
        added, changed = [], []
        for c in d['state'].get('cuts') or []:
            k0 = (c['scope'], norm_item(c['item']))
            if episode and not in_episode(episode, first_named[k0], c.get('fiscal_year')):
                # first named in another episode: keep only if this is a status change
                if k0 not in cuts or cuts[k0]['status'] == c['status']:
                    continue
            elif not keep(d['meeting_date'], c.get('fiscal_year')):
                continue
            # An increase filed as a cut is a restoration: "restore the principal to full
            # time" is not a reduction whatever list it was read from.
            if RESTORE.search(c['item']) and not re.search(r'\b(cut|reduc|eliminat)', c['item'], re.I) and c['status'] not in ('restored', 'withdrawn'):
                c = dict(c, status='restored')
            k = (c['scope'], norm_item(c['item']))
            row = dict(base, **c, video_url='%s&t=%ds' % (d['video_url'], c['t']), key=norm_item(c['item']))
            if k not in cuts:
                added.append(row)
            elif cuts[k]['status'] != c['status']:
                changed.append(dict(row, was=cuts[k]['status']))
            cuts[k] = row
        if added or changed:
            log.append(dict(base, added=[r['item'] for r in added], changed=[dict(item=r['item'], was=r['was'], now=r['status']) for r in changed],
                            n_added=len(added), n_changed=len(changed)))
    log.sort(key=lambda x: x['date'], reverse=True)
    cut_list = sorted(cuts.values(), key=lambda r: (r['scope'], r['status'] in ('restored', 'withdrawn'), r['date']), reverse=False)
    live = [r for r in cut_list if r['status'] not in ('restored', 'withdrawn')]
    read = [d for d in docs if not episode or in_episode(episode, d['meeting_date'], None)]
    return dict(
        meetings_read=len(read), first_date=read[0]['meeting_date'] if read else None, last_date=read[-1]['meeting_date'] if read else None,
        latest={'%s/%s' % k: v for k, v in latest.items()},
        history={'%s/%s' % k: sorted(v, key=lambda r: r['date'], reverse=True) for k, v in history.items()},
        cuts=cut_list, live_cuts=len(live),
        live_by_scope=dict(collections.Counter(r['scope'] for r in live)),
        log=log)


def season_outcome(fy, opens, closes, as_of):
    """HOW THE SEASON LANDED, from the registries and not from captions. TJ: "for last
    year, how it landed at town meeting vote, failing the override, should be clearly
    visible at the top." The ballot questions in the season, with their tallies, from
    sources/data/ballot-questions.csv (each row reconciled to its printed tally); the
    Annual Town Meeting date -- the first Saturday in May of the closing year; and the
    school appropriation the model carries for that year, where it does."""
    year = int((closes or as_of)[:4])
    # first Saturday in May
    d = dt.date(year, 5, 1)
    atm = (d + dt.timedelta(days=(5 - d.weekday()) % 7)).isoformat()
    lo = opens or '%d-05-21' % (fy - 2)
    hi = closes or as_of
    questions = []
    for r in read_csv(BALLOTS):
        if not r['date']:
            continue
        if len(r['date']) == 7:
            # A month-only date (the annual reports print "2025-05"): the May of a season's
            # CLOSE belongs to it; the May of its opening belongs to the season before.
            if not (lo[:7] < r['date'] <= hi[:7]):
                continue
        elif not (lo <= r['date'] <= hi):
            continue
        if r['type'] not in ('Proposition 2½ override', 'Proposition 2½ debt exclusion'):
            continue
        questions.append(dict(date=r['date'], election=r['election'], question=r['question'], type=r['type'],
                              amount=float(r['amount']) if r['amount'] else None, purpose=r['purpose'],
                              yes=int(r['yes']) if r['yes'] else None, no=int(r['no']) if r['no'] else None,
                              total=int(r['total']) if r['total'] else None, registered=int(r['registered']) if r['registered'] else None,
                              turnout_pct=float(r['turnout_pct']) if r['turnout_pct'] else None, result=r['result'], checks=r['checks']))
    model = load(MODEL)
    adopted = None
    if fy == 2027 and model.get('fy27'):
        adopted = dict(amount=model['fy27']['lps_appropriation'], label='school appropriation adopted at the Annual Town Meeting',
                       source='model/finance.py FY27, the balanced scenario voted 2 May 2026')
    closed = bool(closes) and closes <= as_of
    overrides = [q for q in questions if q['type'] == 'Proposition 2½ override']
    if closed and overrides:
        results = {q['result'] for q in overrides}
        if results == {'FAILED'}:
            headline = 'The override failed' if len(overrides) == 1 else 'Both override questions failed'
        elif results == {'PASSED'}:
            headline = 'The override passed'
        elif results <= {'NOT PLACED ON BALLOT'}:
            headline = 'No override reached the ballot'
        else:
            headline = 'Override questions: ' + ', '.join('%s %s' % (q['question'].lower(), q['result'].lower()) for q in overrides)
    elif closed:
        headline = 'No override question this season'
    else:
        headline = 'The season is under way'
    return dict(closed=closed, atm_date=atm if closed else None, election_date=closes or None, questions=questions,
                adopted=adopted, headline=headline)


def what_people_ask(state, outcome, calendar, entries, upcoming, notices, as_of, fy):
    """THE QUESTIONS PEOPLE BRING TO THIS PAGE, answered from the record or marked not yet.

    TJ, 14 September 2026: "How big is the deficit this year? How many teachers? What are
    they planning to cut? What's the status, is it final? What are the next steps? Do they
    need select board approval? Are there open questions? When do they need to have final
    numbers in by? When does the warrant close so citizens can file a petition? Has anyone
    filed a petition for the budget? If so, how much? Are they cutting athletics this year?
    Band? What else?"

    Each answer names where it came from. "Not on the record yet" is an answer too -- in
    September it is the right one for most of these, and a page that says so plainly is
    worth more than one that guesses."""
    latest = state['latest']
    live = [c for c in state['cuts'] if c['status'] not in ('restored', 'withdrawn')]
    ahead = [c for c in calendar if c['status'] in ('ahead', 'now', 'underway')]
    def stage(key):
        return next((c for c in calendar if c['key'] == key), None)
    def has(words):
        rx = re.compile(words, re.I)
        return [c for c in live if rx.search(c['item'])]
    def fte_sum():
        tot = 0.0
        for c in live:
            m = re.search(r'\d+(?:\.\d+)?', c.get('fte_as_heard') or '')
            if m:
                tot += float(m.group(0))
        return tot
    qs = []
    LABELS = {'How big is the school deficit?': 'School deficit', 'How big is the town deficit?': 'Town deficit',
              'What are they planning to cut?': 'Cuts named', 'How many teachers or positions?': 'Positions',
              'Are they cutting athletics this year?': 'Athletics', 'Band? Music? Arts?': 'Band, music, arts',
              'Is it final?': 'Status', 'What’s the status — is it final?': 'Status', 'What are the next steps?': 'Next',
              'When does the warrant close, so a citizen can file a petition?': 'Warrant and petitions',
              'When do they need final numbers by?': 'Final numbers due', 'Does the school budget need Select Board approval?': 'Who decides',
              'Has anyone filed a petition for the budget?': 'Petitions filed', 'Are there open questions?': 'Open questions'}
    def q(question, answer, status, link=None, basis=None):
        qs.append(dict(question=question, label=LABELS.get(question, question), answer=answer, status=status, link=link, basis=basis))
    # the deficit
    for scope, label in (('school', 'the school'), ('town', 'the town')):
        d = latest.get('%s/deficit' % scope)
        if d:
            q('How big is %s deficit?' % label, '%s (%s, %s, %s)' % (d['amount_as_heard'], d['who'], d['board'], d['date']),
              'final' if outcome['closed'] else d['status'], d['video_url'], 'as heard in the recording')
        elif scope == 'school':
            q('How big is the school deficit?', 'Not on the record yet this season.', 'not yet')
    # cuts
    if live:
        athletics = has(r'\b(athletic\w*|sports?|coach\w*)\b'); band = has(r'\b(band|music|chorus|art|arts|drama|theater)\b'); teachers = has(r'\b(teacher\w*|classroom|para\w*|aide\w*)\b')
        q('What are they planning to cut?', '%d reductions named so far%s.' % (len(live), ' — ' + '; '.join(c['item'] for c in live[:4]) + (' …' if len(live) > 4 else '')),
          'final' if outcome['closed'] else 'preliminary', '#cuts')
        q('How many teachers or positions?', ('%.1f FTE named across the cuts, as heard' % fte_sum()) if fte_sum() else ('%d position-related cuts named; FTE not stated' % len(teachers) if teachers else 'No teaching positions named yet.'),
          'preliminary' if not outcome['closed'] else 'final', '#cuts')
        few = lambda xs: '%d named — %s%s' % (len(xs), '; '.join(c['item'] for c in xs[:3]), ' …' if len(xs) > 3 else '')
        q('Are they cutting athletics this year?', few(athletics) if athletics else 'Not named among the cuts so far.', 'preliminary' if not outcome['closed'] else 'final', '#cuts')
        q('Band? Music? Arts?', few(band) if band else 'Not named among the cuts so far.', 'preliminary' if not outcome['closed'] else 'final', '#cuts')
    else:
        q('What are they planning to cut?', 'No cut has been named on the record yet this season.', 'not yet')
    # status
    if outcome['closed']:
        q('Is it final?', 'Yes — the season closed with the election on %s. %s.' % (outcome['election_date'], outcome['headline']), 'final', '#top')
    else:
        t = latest.get('school/budget_total') or latest.get('town/budget_total')
        q('What’s the status — is it final?', ('The latest budget total on the record is %s, %s (%s, %s). Not final: nothing is until Town Meeting votes it.' % (t['amount_as_heard'], t['status'], t['board'], t['date'])) if t else 'No budget total has been put on the record yet; nothing is final until Town Meeting votes it.', 'preliminary' if t else 'not yet', t and t['video_url'])
    # next steps
    if ahead and not outcome['closed']:
        nxt = ahead[0]
        q('What are the next steps?', '%s — typically %s to %s%s.' % (nxt['stage'], nxt['typical_first'], nxt['typical_last'], ('; then ' + ', '.join(c['stage'].lower() for c in ahead[1:3])) if len(ahead) > 1 else ''), 'measured', '#calendar', 'from the boards’ own agendas over five cycles')
    # deadlines
    wc = stage('warrant-closes')
    q('When does the warrant close, so a citizen can file a petition?',
      ('In past cycles the Select Board opened and closed the warrant between %s and %s. Ten registered voters can place an article on an annual Town Meeting warrant, a hundred on a special one (M.G.L. c. 39 § 10), before it closes.' % (wc['typical_first'], wc['typical_last'])) if wc else 'Ten registered voters can place an article on an annual Town Meeting warrant, a hundred on a special one (M.G.L. c. 39 § 10), before the Select Board closes it; the closing date is posted with the warrant.',
      'measured' if wc else 'statute', '#calendar')
    bv = stage('budget-vote')
    if bv and not outcome['closed']:
        q('When do they need final numbers by?', 'The School Committee’s budget vote has fallen %s to %s; Town Meeting is the first Saturday in May.' % (bv['typical_first'], bv['typical_last']), 'measured', '#calendar')
    q('Does the school budget need Select Board approval?', 'The School Committee votes the school budget; the Finance Committee reports on it to Town Meeting (Charter § 2-1(c)); Town Meeting appropriates it. The Select Board places the warrant and, for an override, the ballot question.', 'charter', '/boards/finance-committee')
    # petitions
    pet = [e for e in entries if re.search(r'citizen\w*\s+petition', (e.get('text') or '') + ' ' + (e.get('detail') or ''), re.I)]
    petq = [x for x in outcome['questions'] if 'petition' in (x['question'] + x['purpose']).lower()]
    if petq:
        x = petq[0]
        q('Has anyone filed a petition for the budget?', '%s — %s%s.' % (x['question'], ('$' + format(int(x['amount']), ',') + ' ') if x['amount'] else '', x['result'].lower()), 'recorded', '#top')
    elif pet:
        q('Has anyone filed a petition for the budget?', 'A citizens’ petition came up at %s on %s: %s' % (pet[0]['board'], pet[0]['date'], (pet[0].get('text') or '')[:120]), 'on the record', pet[0].get('video_url') or pet[0]['page'])
    else:
        q('Has anyone filed a petition for the budget?', 'None on the record this season.', 'not yet')
    # open questions: budget topics our minutes marked as discussed only / deferred
    openq = [e for e in entries if e['kind'] == 'topic' and re.search(r'discuss|defer|tabled|no decision|informational|continued', (e.get('detail') or ''), re.I)][:5]
    if openq:
        q('Are there open questions?', 'Discussed without a decision: ' + '; '.join('%s (%s, %s)' % (e['text'], e['board'], e['date']) for e in openq), 'on the record', '#recent')
    return qs


def propose_episodes(eps, docs, names, notices, as_of):
    """SIGNS THAT A NEW EPISODE HAS STARTED, proposed for a person to confirm -- never created
    here. TJ, 14 September 2026: "as you discover info through the meeting minutes, [you]
    can figure out 'hey it looks like something started a new episode' and we can create
    one." Four signals, each with its evidence:
      * a Special Town Meeting DATE named in a notice or on an agenda that no episode covers
      * an override question on an agenda outside any episode window
      * the Governor's budget / cherry sheet on a budget board's agenda after July, outside a window
      * the first proposed-budget agenda of a cycle, with no regular episode open
    Written into the payload as `proposed_episodes` (not rendered) and printed by the
    refresh with the rest of the day's notes."""
    covered = lambda d: any((not e['opens'] or e['opens'] <= d) and (not e['closes'] or d <= e['closes']) for e in eps)
    since = (dt.date.fromisoformat(as_of) - dt.timedelta(days=60)).isoformat()
    out, seen = [], set()
    STM = re.compile(r'special\s+town\s+meeting[^.\n]{0,60}?(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:,?\s*(\d{4}))?', re.I)
    MONTHS_FULL = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
    def stm_dates(text):
        for m in STM.finditer(text or ''):
            mon = MONTHS_FULL.index(m.group(1).lower()) + 1
            yr = int(m.group(3)) if m.group(3) else int(as_of[:4])
            try:
                yield dt.date(yr, mon, int(m.group(2))).isoformat()
            except ValueError:
                continue
    for n in notices:
        for d in stm_dates(n['title']):
            if d > (n['published'] or n['first_seen']) and not covered(d) and ('stm', d) not in seen:
                seen.add(('stm', d)); out.append(dict(kind='special', signal='a Special Town Meeting on %s' % d, evidence='%s — %s' % (n['source'], n['title']), link=n['link'], suggested=dict(id='stm-' + d, opens=n['published'] or n['first_seen'], closes=d)))
    for slug, by_date in docs.items():
        if slug not in ('select-board', 'finance-committee', 'school-committee'):
            continue
        for d, kinds in by_date.items():
            if d < since or d > as_of or 'agenda' not in kinds:
                continue
            text = agenda_text(slug, kinds['agenda'])
            for sd in stm_dates(text):
                if sd > d and not covered(sd) and ('stm', sd) not in seen:   # a date after the agenda: a meeting to come, not one recalled
                    seen.add(('stm', sd)); out.append(dict(kind='special', signal='a Special Town Meeting on %s' % sd, evidence='%s agenda, %s' % (names.get(slug, slug), d), link='/docs/meetings/' + kinds['agenda']['path'], suggested=dict(id='stm-' + sd, opens=d, closes=sd)))
            if not covered(d):
                if re.search(r'\boverride\b', text, re.I) and ('override', d[:7]) not in seen:
                    seen.add(('override', d[:7])); out.append(dict(kind='special', signal='an override on the agenda outside any episode', evidence='%s agenda, %s' % (names.get(slug, slug), d), link='/docs/meetings/' + kinds['agenda']['path'], suggested=dict(id='override-' + d[:7], opens=d)))
                if re.search(r"governor.?s\s+budget|cherry\s+sheet|chapter\s*70", text, re.I) and ('aid', d[:7]) not in seen:
                    seen.add(('aid', d[:7])); out.append(dict(kind='special', signal='state aid / the Governor’s budget on the agenda outside any episode', evidence='%s agenda, %s' % (names.get(slug, slug), d), link='/docs/meetings/' + kinds['agenda']['path'], suggested=dict(id='state-aid-' + d[:7], opens=d)))
                if re.search(r'(proposed|preliminary|superintendent.?s)\s+(fy\s*\d+\s+)?budget|budget\s+presentation', text, re.I) and not any(e['kind'] == 'regular' and (not e['opens'] or e['opens'] <= d) for e in eps) and ('season', d[:7]) not in seen:
                    seen.add(('season', d[:7])); out.append(dict(kind='regular', signal='a budget presented — the regular season may have opened', evidence='%s agenda, %s' % (names.get(slug, slug), d), link='/docs/meetings/' + kinds['agenda']['path'], suggested=dict(id='fy%d-season' % (fy_of_date(d) % 100), opens=d)))
    return out


def build(as_of=None, whole_cycle=False):
    as_of = as_of or dt.date.today().isoformat()
    since = (dt.date.fromisoformat(as_of) - dt.timedelta(days=RECENT_DAYS)).isoformat()
    if whole_cycle:       # a season replay: everything since the season opened
        since = cycle_start(as_of)
    doc_since = (dt.date.fromisoformat(as_of) - dt.timedelta(days=DOC_DAYS)).isoformat()
    idx = read_csv(INDEX)
    docs = collections.defaultdict(lambda: collections.defaultdict(dict))
    names = {}
    for r in idx:
        if r['path']:
            slug = r['path'].split('/')[0]
            docs[slug][r['date']][r['kind']] = r
            names.setdefault(slug, r['board'])
    rec = load(RECORDED)
    notices = load(NOTICES)
    boards = {b['slug']: b for b in load(BOARDS).get('boards', [])}
    previews = {(n['board_slug'], n['date']): n for n in notices.get('upcoming', [])}

    # 1. upcoming, filtered by the agenda's own words
    # From the meetings index rather than the live feed payload, so a replay at any date
    # sees the agendas that were posted for the four weeks after it.
    horizon = (dt.date.fromisoformat(as_of) + dt.timedelta(days=28)).isoformat()
    coming = []
    for slug, by_date in docs.items():
        for d, kinds in by_date.items():
            if 'agenda' in kinds and as_of <= d <= horizon:
                coming.append(dict(board=names.get(slug, slug), board_slug=slug, date=d, agenda_url=kinds['agenda']['url'],
                                   days_away=(dt.date.fromisoformat(d) - dt.date.fromisoformat(as_of)).days))
    upcoming, seen_up = [], set()
    for u in sorted(coming, key=lambda x: (x['date'], x['board'])):
        if (u['board_slug'], u['date']) in seen_up:
            continue          # two agendas for one date (a revision) are one meeting
        seen_up.add((u['board_slug'], u['date']))
        row = docs[u['board_slug']].get(u['date'], {}).get('agenda')
        text = agenda_text(u['board_slug'], row) if row else ''
        h = hits(text)
        if not h:
            continue
        pv = previews.get((u['board_slug'], u['date']))
        items = [it for it in (pv or {}).get('items') or [] if MARKER.search(it.get('agenda_line', '') + ' ' + (it.get('why_it_matters') or ''))]
        upcoming.append(dict(board=u['board'], board_slug=u['board_slug'], date=u['date'], days_away=u['days_away'],
                             agenda_url=u['agenda_url'], markers=h, hook=pv and pv.get('hook'), time=pv and pv.get('time'),
                             where=pv and pv.get('where'), attend=pv and pv.get('attend'), join=pv and pv.get('join'),
                             items=items[:6], board_page='/boards/' + u['board_slug']))
    upcoming.sort(key=lambda x: (x['date'], x['board']))

    # 2. the calendar, this cycle
    tp = today_pos(as_of)
    # The season being built, by the election-day cycles: after 16 May 2026 is FY2028's.
    fy_now = fy_of_date(as_of)
    opens, closes = cycle_span(fy_now)
    calendar = []
    for label, key, leads in STAGES:
        windows = []
        for slug in leads:
            b = boards.get(slug)
            cal = next((c for c in (b or {}).get('calendar', []) if c['key'] == key), None)
            if cal:
                windows.append(dict(board=b['name'], board_slug=slug, typical_first=cal['typical_first'], typical_last=cal['typical_last'],
                                    earliest=cal['earliest'], latest=cal['latest'], cycles=len(cal['cycles']),
                                    this_cycle=[d for c in cal['cycles'] if c['fy'] == fy_now for d in c['dates']]))
        if not windows:
            continue
        first = min(cycle_pos(w['typical_first']) for w in windows)
        last = max(cycle_pos(w['typical_last']) for w in windows)
        status = 'past' if tp > last else ('now' if tp >= first else 'ahead')
        if any(w['this_cycle'] for w in windows):
            status = 'underway' if status != 'past' else 'past'
        calendar.append(dict(stage=label, key=key, windows=windows, status=status,
                             typical_first=MONTHS[first // 31] + ' ' + str(first % 31 or 1),
                             typical_last=MONTHS[last // 31] + ' ' + str(last % 31 or 1)))

    # 3. recent discussion, newest first
    entries = []
    for m in rec.get('meetings', []):
        if m['date'] < since or m['date'] >= as_of:
            continue          # today's meeting has not happened; it is in 'coming up'
        mins = m['minutes']
        page = '/meeting-minutes/' + m['slug']
        for t in mins.get('topics') or []:
            tags = [x for x in (t.get('tags') or []) if x in BUDGET_TAGS]
            if not tags:
                continue
            entries.append(dict(kind='topic', board=m['board'], board_slug=m['board_slug'], date=m['date'], page=page,
                                text=t['topic'], detail=tally_only(t.get('resolution')), tags=tags, t=t.get('t_start'),
                                video_url='%s&t=%ds' % (m['video_url'], t['t_start']) if t.get('t_start') is not None else m['video_url'],
                                minutes=round(((t.get('t_end') or 0) - (t.get('t_start') or 0)) / 60)))
        for bi in mins.get('budget_items') or []:
            if not MARKER.search((bi.get('topic') or '') + ' ' + (bi.get('what_was_said') or '')):
                continue
            entries.append(dict(kind='budget item', board=m['board'], board_slug=m['board_slug'], date=m['date'], page=page,
                                text=bi.get('topic'), detail=bi.get('what_was_said'), figures=bi.get('figures_as_heard') or [],
                                t=bi.get('t'), video_url='%s&t=%ds' % (m['video_url'], bi['t']) if bi.get('t') is not None else m['video_url']))
        for v in mins.get('votes') or []:
            if v.get('procedural') or not MARKER.search(v.get('motion') or '') or APPOINTMENT.match(v.get('motion') or '') or HOUSEKEEPING.match(v.get('motion') or ''):
                continue
            entries.append(dict(kind='vote', board=m['board'], board_slug=m['board_slug'], date=m['date'], page=page,
                                text=v.get('motion'), detail=tally_only(v.get('outcome')), t=v.get('t'),
                                video_url='%s&t=%ds' % (m['video_url'], v['t']) if v.get('t') is not None else m['video_url']))
    ours = {(m['board_slug'], m['date']) for m in rec.get('meetings', [])}
    for slug, by_date in docs.items():
        for d, kinds in by_date.items():
            if d < since or d >= as_of or (slug, d) in ours:
                continue
            for kind in ('minutes', 'agenda'):
                row = kinds.get(kind)
                if not row:
                    continue
                h = hits(agenda_text(slug, row))
                if h:
                    entries.append(dict(kind='official ' + kind, board=names.get(slug, slug), board_slug=slug, date=d,
                                        page='/docs/meetings/' + row['path'], text=', '.join(h), detail=None, markers=h))
                    break     # minutes over agenda for the same date
    entries.sort(key=lambda e: (e['date'], e.get('t') or 0), reverse=True)

    # 4. documents and notices
    documents = []
    for r in read_csv(DOC_EVENTS):
        if r.get('first_seen', '') >= doc_since:
            documents.append(dict(first_seen=r['first_seen'], source=r.get('source') or r.get('page') or '', title=r.get('title') or r.get('label') or '', url=r.get('url') or r.get('upstream') or ''))
    notices_out = []
    for r in read_csv(FEED_EVENTS):
        if r['first_seen'] >= doc_since and MARKER.search(r['title']):
            notices_out.append(dict(first_seen=r['first_seen'], source=r['source'], published=r['published'], title=r['title'], link=r['link']))
    notices_out.sort(key=lambda x: x['published'] or x['first_seen'], reverse=True)

    outcome = season_outcome(fy_now, opens, closes, as_of)
    eps = episodes_for(fy_now)
    episodes = []
    for ep in eps:
        if ep['opens'] and ep['opens'] > as_of:
            continue
        st = budget_state(as_of, ep)
        episodes.append(dict(ep, closed=bool(ep['closes']) and ep['closes'] <= as_of, state=st,
                             answers=what_people_ask(st, outcome, calendar, entries, upcoming, notices_out, as_of, fy_now) if ep['kind'] == 'regular' else None))
    proposed = propose_episodes(eps, docs, names, notices_out, as_of) if not whole_cycle else []
    # the whole season, for the tracker sections below; the regular episode's answers for the glance
    state = budget_state(as_of)
    regular = next((e for e in episodes if e['kind'] == 'regular'), None)
    answers = regular['answers'] if regular else what_people_ask(state, outcome, calendar, entries, upcoming, notices_out, as_of, fy_now)
    # THE SAME LIST IN EVERY PAYLOAD: the live cycle is today's, whatever this payload's
    # as_of is, and every replay file present is a season. A replay must not call itself live.
    live_fy = fy_of_date(dt.date.today().isoformat())
    seasons = [dict(fy=live_fy, path='/budget-feed', label='FY%d, live' % (live_fy % 100), live=True)]
    for f in sorted(glob.glob(os.path.join(DATA, 'budget-feed-fy*.json')), reverse=True):
        tag = os.path.basename(f)[len('budget-feed-'):-5]
        fy = 2000 + int(tag[2:])
        if fy != live_fy:
            seasons.append(dict(fy=fy, path='/budget-feed/' + tag, label='FY%d, the season replayed' % (fy % 100), live=False))
    if whole_cycle and not any(x['fy'] == fy_now for x in seasons):
        seasons.append(dict(fy=fy_now, path='/budget-feed/fy%d' % (fy_now % 100), label='FY%d, the season replayed' % (fy_now % 100), live=False))
    seasons.sort(key=lambda x: -x['fy'])
    # The episodes of the live season are choices too -- TJ: "the governor situation should
    # show up in the dropdown." Listed under their season, newest first.
    eps_opts = [dict(fy=fy_now, path='/budget-feed/' + e['id'], label='  ↳ ' + e['label'], live=not e['closed'], episode=e['id'])
                for e in sorted(episodes, key=lambda e: e['opens'] or '', reverse=True) if e['kind'] == 'special']
    live_at = next((i for i, x in enumerate(seasons) if x.get('live')), 0)
    seasons[live_at + 1:live_at + 1] = eps_opts     # directly under the live season
    by_board = collections.Counter(e['board'] for e in entries)
    return dict(
        about=('What every board is doing to prepare for Town Meeting: the omnibus budget, the school budget above all, '
               'and the warrant. What is coming, where this cycle stands, what was said most recently, what was posted. '
               'Not every mention of money — the budget being built, and what will land on the warrant.'),
        as_of=as_of, cycle_fy=fy_now, cycle_opens=opens, cycle_closes=closes, recent_days=(dt.date.fromisoformat(as_of) - dt.date.fromisoformat(since)).days, whole_cycle=whole_cycle,
        upcoming=upcoming, calendar=calendar, entries=entries, documents=documents, notices=notices_out, state=state, seasons=seasons, outcome=outcome, answers=answers, episodes=episodes, proposed_episodes=proposed,
        counts=dict(upcoming=len(upcoming), entries=len(entries), boards=len(by_board), by_board=dict(by_board.most_common()),
                    kinds=dict(collections.Counter(e['kind'] for e in entries))),
        markers=sorted(set(w for u in upcoming for w in u['markers'])),
        generated_by='scripts/build_budget_feed.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--as-of')
    ap.add_argument('--out', help='write to this file instead of budget-feed.json (a season replay)')
    a = ap.parse_args()
    global OUT
    if a.out:
        OUT = os.path.join(ROOT, a.out) if not os.path.isabs(a.out) else a.out
    if a.check:
        have = load(OUT) or None
        data = build(have['as_of'] if have else None)
        if have != data:
            print('STALE %s — run build_budget_feed.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    data = build(a.as_of, whole_cycle=bool(a.out))
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    c = data['counts']
    print('%s: as of %s — %d upcoming budget meetings, %d recent entries across %d boards (%s), %d stages on the calendar'
          % (os.path.relpath(OUT, ROOT), data['as_of'], c['upcoming'], c['entries'], c['boards'],
             ', '.join('%s %d' % kv for kv in c['kinds'].items()), len(data['calendar'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
