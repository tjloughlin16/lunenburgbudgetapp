#!/usr/bin/env python3
"""One page per board: upcoming, recent, every vote in recency order, where the time goes,
and when budget season has fallen on that board's agendas in past years.

    python3 scripts/build_boards.py          # write fy28/public/data/boards.json
    python3 scripts/build_boards.py --check  # fail if it no longer reproduces

TJ, 14 September 2026: "pages specifically built for each board, committee so we can see
upcoming, recent, meeting minutes, etc all in one place for them, including all votes in
recency order. We can also build budget season expected timelines from past timelines."

EVERYTHING IS READ FROM WHAT THE OTHER GENERATORS ALREADY HOLD. The meetings index (every
agenda and set of minutes the town posted, by board), the recording register (every video
by board), our recording minutes (votes, topics, digests, time by topic), the meeting feed
(what is coming), the notices (our agenda previews). Nothing is fetched or written by a
model here; a board page is a JOIN.

THE BUDGET CALENDAR IS MEASURED, NOT ASSERTED. For each of the last five budget cycles
(July to June), the dates on which this board's own AGENDA text carried the words that mark
the season -- a budget item, a public hearing, Town Meeting, an override -- are read off
the extracted agendas. The page shows those dates per cycle and the earliest and latest
across cycles as the window to expect. A word on an agenda is not a decision: it says the
board scheduled the subject, which is what a resident planning to attend needs.
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
from budget_cycles import fy_of as cycle_fy_of   # noqa: E402
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')
VIDEOS = os.path.join(ROOT, 'sources', 'data', 'youtube-video-boards.csv')
CLASS = os.path.join(ROOT, 'sources', 'data', 'youtube-video-classification.csv')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
NOCAP = os.path.join(ROOT, 'sources', 'data', 'youtube-no-captions.csv')
RECORDED = os.path.join(ROOT, 'fy28', 'public', 'data', 'recording-minutes.json')
FEED = os.path.join(ROOT, 'fy28', 'public', 'data', 'meeting-feed.json')
NOTICES = os.path.join(ROOT, 'fy28', 'public', 'data', 'notices.json')
PAGES = os.path.join(ROOT, 'sources', 'data', 'board-pages.csv')
DISTRICT_INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
MINUTES_LAG_DAYS = 60   # minutes are approved at the next meeting and posted after it
VIDEO_LAG_DAYS = 7      # a recording is up within days, or it is not coming
# THE COMMITTEE'S OWN DOCUMENTS ABOUT ITSELF, from the district's meetings page as the
# crawler files it (page = sc-meetings): the operating protocols and the meeting
# calendar, latest school year of each. TJ, 17 September 2026: "post the new 'operating
# procedures' directly on the school committee page in the app for reference."
ABOUT_ITSELF = (('protocols', r'operating protocols'), ('calendar', r'meeting calendar'))


def about_itself(slug):
    if slug != 'school-committee' or not os.path.exists(DISTRICT_INDEX):
        return []
    rows = [r for r in csv.DictReader(open(DISTRICT_INDEX, encoding='utf-8'))
            if r.get('page') == 'sc-meetings' and r.get('local')]
    out = []
    for key, pat in ABOUT_ITSELF:
        hits = sorted((r for r in rows if re.search(pat, r['label'], re.I)), key=lambda r: r.get('school_year') or '', reverse=True)
        if not hits:
            continue
        r = hits[0]
        text = ''
        if r.get('text') and os.path.exists(os.path.join(ROOT, r['text'])):
            text = re.sub(r'===PAGE \d+===\n?', '', open(os.path.join(ROOT, r['text']), encoding='utf-8', errors='replace').read()).strip()
        out.append(dict(key=key, label=r['label'], school_year=r.get('school_year') or '', url='/docs/' + r['local'][len('sources/'):],
                        upstream=r['upstream'], sha256=r['sha256'], text=text if key == 'protocols' else ''))
    return out
CHARTER_URL = 'https://www.lunenburgma.gov/323/Charter-Town-Bylaws'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'boards.json')
SITE = 'https://lunenburgbudgetproject.org'
RECENT = 15
CYCLES = 5

# THE THREE, first on the index and richest on their pages.
THE_THREE = ['school-committee', 'select-board', 'finance-committee']

# What marks budget season on an agenda. Each is a regex over the agenda's extracted text,
# case-insensitive; a date counts once per marker however many times the word appears.
MARKERS = [
    ('budget-presentation', 'a budget presented or reviewed',
     r'(proposed|preliminary|draft|superintendent.?s|town manager.?s)\s+(fy\s*\d+\s+)?budget|budget\s+(presentation|overview|update|review|discussion|workshop)'),
    ('budget-hearing', 'a budget hearing', r'budget\s+(public\s+)?hearing|(public\s+)?hearing\W{0,40}budget'),
    ('budget-vote', 'a budget vote', r'(vote|approve|approval|adopt|adoption)\W{0,3}(of|on|the)?\W{0,3}(the\s+)?(fy\s*\d+\s+)?budget|budget\W{0,20}(vote|approval|adoption)'),
    ('town-meeting', 'Town Meeting', r'town\s+meeting'),
    ('override', 'an override', r'\boverride\b'),
    ('warrant', 'warrant articles', r'warrant\s+article'),
    ('warrant-closes', 'the warrant closes', r'clos\w*\s+(?:of\s+)?(?:the\s+)?warrant|warrant\s+(?:is\s+)?clos\w*|open\s+(?:the\s+)?warrant|warrant\s+(?:is\s+)?(?:now\s+)?open'),
    ('petition', 'a citizens’ petition', r'citizen\w*\s+petition'),
]
MONTHS = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']


def cycle_pos(date):
    """Position inside a season, which opens after the May election: (months since June, day)."""
    m, d = int(date[5:7]), int(date[8:10])
    return ((m - 6) % 12, d)


def pos_text(pos):
    return '%s %d' % (MONTHS[pos[0]], pos[1])



def read_csv(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8'))) if os.path.exists(p) else []


def fy_of(date):
    """The season a date belongs to, by the town's election-day cycles (budget_cycles.py)."""
    return cycle_fy_of(date)


def plain_fy(date):
    """The ordinary fiscal year, July to June -- what 'FY27' means on a scorecard, as
    against the budget SEASON above, which turns over at the May election."""
    y = int(date[:4])
    return y + 1 if date[5:7] >= '07' else y


def build(as_of=None):
    as_of = as_of or dt.date.today().isoformat()
    idx = read_csv(INDEX)
    docs = collections.defaultdict(lambda: collections.defaultdict(dict))   # slug -> date -> kind -> row
    names = {}
    for r in idx:
        if not r['path']:
            continue
        slug = r['path'].split('/')[0]
        names.setdefault(slug, r['board'])
        docs[slug][r['date']][r['kind']] = r
    vids = collections.defaultdict(dict)                                     # slug -> date -> video row
    cls = {r['video_id']: r for r in read_csv(CLASS)}
    for r in read_csv(VIDEOS):
        if cls.get(r['video_id'], {}).get('kind') == 'meeting' and r['meeting_date']:
            vids[r['board_slug']][r['meeting_date']] = r
            names.setdefault(r['board_slug'], r['board_name'])
    trans = {(r['board_slug'], r['meeting_date']): r for r in read_csv(TRANSCRIPTS)}
    nocap = {(r['board_slug'], r['meeting_date']) for r in read_csv(NOCAP)}
    rec = json.load(open(RECORDED, encoding='utf-8'))
    ours = collections.defaultdict(dict)
    for m in rec['meetings']:
        ours[m['board_slug']][m['date']] = m
    feed = json.load(open(FEED, encoding='utf-8'))
    notices = json.load(open(NOTICES, encoding='utf-8'))
    previews = {(n['board_slug'], n['date']): n for n in notices.get('upcoming', [])}
    # The board's own page on the town's (or the district's) site: what it is, in the
    # publisher's words, its members, when it meets, and a Facebook link where the page
    # carries one. fetch_board_pages.py mirrors and extracts; nothing is paraphrased here.
    pages = {r['slug']: r for r in read_csv(PAGES)}

    boards = []
    for slug in sorted(set(docs) | set(vids)):
        if not slug:
            continue
        name = names.get(slug, slug)
        dates = sorted(set(docs[slug]) | set(vids[slug]) | set(ours[slug]), reverse=True)
        past = [d for d in dates if d <= as_of]
        # --- upcoming: the feed's rows for this board, with our preview where one exists
        upcoming = []
        for u in feed['upcoming']['meetings']:
            if u['board_slug'] != slug:
                continue
            pv = previews.get((slug, u['date']))
            upcoming.append(dict(date=u['date'], days_away=u['days_away'], agenda_url=u['agenda_url'],
                                 hook=pv and pv.get('hook'), time=pv and pv.get('time'), where=pv and pv.get('where'),
                                 attend=pv and pv.get('attend'), important=pv and pv.get('important'),
                                 items=pv and pv.get('items'), join=pv and pv.get('join')))
        # --- recent meetings, one row each
        recent = []
        for d in past[:RECENT]:
            a = docs[slug][d].get('agenda'); mn = docs[slug][d].get('minutes'); v = vids[slug].get(d); o = ours[slug].get(d)
            recent.append(dict(
                date=d,
                agenda_url=a and a['url'], agenda_doc=a and ('/docs/meetings/' + a['path']),
                minutes_url=mn and mn['url'], minutes_doc=mn and ('/docs/meetings/' + mn['path']),
                video_url=v and ('https://www.youtube.com/watch?v=' + v['video_id']),
                transcript=(slug, d) in trans, captions_disabled=(slug, d) in nocap,
                ours=o and dict(slug=o['slug'], headline=o.get('headline'), digest=o.get('digest'),
                                votes=o['counts'].get('votes'), reconciled=o.get('has_official_minutes'),
                                discrepancies=o.get('discrepancies'))))
        # --- every vote we have minutes for, newest first, with the second in the video
        votes = []
        for d, o in sorted(ours[slug].items(), reverse=True):
            for v in o['minutes'].get('votes') or []:
                votes.append(dict(date=d, t=v.get('t'), motion=v.get('motion'), outcome=v.get('outcome'),
                                  procedural=bool(v.get('procedural')), moved_by=v.get('moved_by'),
                                  page='/meeting-minutes/' + o['slug'],
                                  video_url='%s&t=%ds' % (o['video_url'], v['t']) if v.get('t') is not None else o['video_url']))
        # --- where the time goes, this board
        tb = rec.get('time_by_board', {}).get(slug) or {}
        span = tb.get('topics_span_s') or 0
        time_by_tag = sorted(({'tag': k, 'label': k.replace('-', ' '), 'seconds': sec, 'share': (sec / span) if span else None}
                              for k, sec in (tb.get('by_tag_s') or {}).items()), key=lambda x: -x['seconds'])[:12]
        time_meetings = tb.get('meetings') or 0
        # --- the budget calendar, from this board's own agendas
        calendar = collections.defaultdict(lambda: collections.defaultdict(list))
        for d, kinds in docs[slug].items():
            a = kinds.get('agenda')
            if not a:
                continue
            p = os.path.join(TEXT, slug, os.path.splitext(os.path.basename(a['path']))[0] + '.txt')
            if not os.path.exists(p):
                continue
            text = open(p, encoding='utf-8', errors='replace').read()
            for key, _label, rx in MARKERS:
                if re.search(rx, text, flags=re.I):
                    calendar[fy_of(d)][key].append(d)
        fys = sorted(calendar)[-CYCLES:]
        cal = []
        for key, label, _ in MARKERS:
            per = {fy: sorted(calendar[fy][key]) for fy in fys if calendar[fy][key]}
            if not per:
                continue
            # Dates inside each cycle sorted by position in the July-June year, so the
            # window reads in budget order and not in calendar order.
            per = {fy: sorted(v, key=cycle_pos) for fy, v in per.items()}
            firsts = sorted(cycle_pos(v[0]) for v in per.values())
            lasts = sorted(cycle_pos(v[-1]) for v in per.values())
            cal.append(dict(key=key, label=label,
                            cycles=[dict(fy=fy, dates=per[fy]) for fy in fys if fy in per],
                            earliest=pos_text(firsts[0]), latest=pos_text(lasts[-1]),
                            typical_first=pos_text(firsts[len(firsts) // 2]), typical_last=pos_text(lasts[len(lasts) // 2]),
                            meetings=sum(len(v) for v in per.values())))
        pg = pages.get(slug)
        page = pg and dict(url=pg['url'], source=pg['source'], overview=pg['overview'], charter_ref=pg['charter_ref'],
                           meets=pg['meets'], members=[m for m in pg['members'].split('\n') if m.strip()],
                           facebook=pg['facebook'] or None, facebook_scope=pg['facebook_scope'],
                           mirror='/docs/' + pg['local'][len('sources/'):], fetched_at=pg['fetched_at'][:10],
                           charter_url=CHARTER_URL)
        # THIS YEAR'S SCORECARD. TJ, 17 September 2026: "put the percentages of the
        # current fiscal year of minutes and video postings on each board's page ... '66%
        # minutes FY27' ... '100% YouTube recordings FY27'". Meetings are dates with a
        # posted agenda in the current fiscal year; minutes are counted only for meetings
        # older than MINUTES_LAG_DAYS (approved at the next meeting, posted after) and
        # recordings for meetings older than VIDEO_LAG_DAYS. Early in a fiscal year the
        # denominators are small and the card says so by printing them.
        this_fy = plain_fy(as_of)
        m_cut = (dt.date.fromisoformat(as_of) - dt.timedelta(days=MINUTES_LAG_DAYS)).isoformat()
        v_cut = (dt.date.fromisoformat(as_of) - dt.timedelta(days=VIDEO_LAG_DAYS)).isoformat()
        def score(fy):
            ms = [d for d in docs[slug] if 'agenda' in docs[slug][d] and plain_fy(d) == fy and d <= as_of]
            m_elig = [d for d in ms if d <= m_cut]
            v_elig = [d for d in ms if d <= v_cut]
            return dict(fy=fy,
                        minutes=dict(meetings=len(m_elig), have=sum(1 for d in m_elig if 'minutes' in docs[slug][d])),
                        recordings=dict(meetings=len(v_elig), have=sum(1 for d in v_elig if d in vids[slug])))
        scorecard = dict(this=score(this_fy), last=score(this_fy - 1), minutes_lag_days=MINUTES_LAG_DAYS, video_lag_days=VIDEO_LAG_DAYS)
        boards.append(dict(
            slug=slug, name=name, the_three=slug in THE_THREE, page=page, about_itself=about_itself(slug), scorecard=scorecard,
            counts=dict(agendas=sum(1 for d in docs[slug] if 'agenda' in docs[slug][d]),
                        minutes=sum(1 for d in docs[slug] if 'minutes' in docs[slug][d]),
                        recordings=len(vids[slug]),
                        transcripts=sum(1 for d in vids[slug] if (slug, d) in trans),
                        captions_disabled=sum(1 for d in vids[slug] if (slug, d) in nocap),
                        our_minutes=len(ours[slug]), votes=len(votes),
                        first=min(dates) if dates else None, last=max(past) if past else None),
            upcoming=upcoming, recent=recent, votes=votes, time_by_tag=time_by_tag, time_meetings=time_meetings, time_span_s=span,
            calendar=cal, calendar_cycles=[fy for fy in fys],
            urls=dict(minutes_text='/minutes/%s.txt' % slug, what_was_said='/meeting-minutes', this_week='/this-week#m-%s' % slug)))
    # The three in their fixed order; every other board alphabetically, so a resident can find theirs.
    boards.sort(key=lambda b: (0 if b['the_three'] else 1, THE_THREE.index(b['slug']) if b['the_three'] else 0, b['name'].lower()))
    return dict(
        about=('Every board and committee the town posts for, one page each: what is coming, what happened, '
               'every vote we have minutes for, where the board’s time goes, and when budget season has '
               'fallen on its agendas in past years.'),
        as_of=as_of, boards=boards, the_three=THE_THREE, markers=[dict(key=k, label=l) for k, l, _ in MARKERS],
        cycles=CYCLES, generated_by='scripts/build_boards.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--as-of')
    a = ap.parse_args()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        data = build(have['as_of'] if have else None)
        if have != data:
            print('STALE %s — run build_boards.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    data = build(a.as_of)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    b = data['boards']
    print('%s: %d boards; %s' % (os.path.relpath(OUT, ROOT), len(b),
          '; '.join('%s %d votes, %d recent' % (x['slug'], x['counts']['votes'], len(x['recent'])) for x in b[:3])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
