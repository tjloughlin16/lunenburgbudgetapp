#!/usr/bin/env python3
"""How the boards post: for every board the town posts for, the share of its meetings
that ever got minutes, by fiscal year -- and whether its meetings are recorded.

    python3 scripts/build_board_posting.py           # write fy28/public/data/board-posting.json
    python3 scripts/build_board_posting.py --check   # fail if it no longer reproduces

TJ, 17 September 2026: "do we have a breakdown of the boards who post minutes? I want
to show the school committee what percent of minutes they have missed compared to
other boards." And then: "having this on a page would be good. a sort of 'board
analysis' page."

WHAT IS MEASURED, EXACTLY. The town's Agenda Center lists, per board, every agenda and
every set of minutes it has posted (sources/meetings/index.csv, one row per document,
kept current by the refresh). A MEETING here is a date a board posted an agenda for.
A meeting HAS MINUTES if the Agenda Center also lists minutes for that board and date.
The share is minutes over meetings. It is a share of the town's own postings and
nothing else: it does not know whether a meeting happened, was cancelled, or had its
minutes filed somewhere the Agenda Center does not list.

THE SCHOOL COMMITTEE IS MEASURED ON THE SAME SHELF. It is a district body with its own
page on lunenburgschools.net -- and that page's "Meeting Agendas & Minutes" link sends
the reader to the town's Agenda Center for minutes. So the Agenda Center is the right
place to count, for it as for every other board. Checked 17 September 2026.

TWO THINGS THAT WOULD OTHERWISE MISLEAD, both handled:
  - THE TAIL. Minutes are approved at the next meeting and posted after that, so the
    last two months of any board look worse than they are. Meetings younger than
    LAG_DAYS are left out of every share, and the page says so.
  - THE LIFETIME NUMBER. All years folded together, the School Committee sits near the
    bottom -- and the reason is one year in which it posted nothing at all, not the
    years since. So the table is by fiscal year, and the conclusions name years.

RULE 7. "Posted fewer minutes" is the measurement. Why -- a clerk vacancy, a policy,
minutes approved but never uploaded -- is not in this data and is not stated. Rule 8:
the page names the board that does this best as the standard, and says of the rest
what the record says.

RECORDINGS come from the town's YouTube channel as classified to a board
(youtube-video-boards.csv): a meeting is RECORDED if a video is classified to that
board and date. Captions-disabled counts are the board payload's.
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C                                           # noqa: E402
from conclusions import conclusion, emit, figure                  # noqa: E402

REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
BOARDS = os.path.join(ROOT, 'fy28', 'public', 'data', 'boards.json')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'board-posting.json')
LAG_DAYS = 60

# POSTED, NOT MERELY HELD. This page measures what the town PUBLISHES -- its own Agenda
# Center, every agenda and every set of minutes it lists -- and the register's `minutes`
# flag answers a different question: does this project hold minutes for that meeting.
#
# The two were the same thing until 18 September 2026, when the Chair of the Select Board
# sent sixteen sets of minutes the town had never posted. They belong in the archive and
# they are the town's own minutes, so the register flags them, and reading that flag here
# would have moved the Select Board's posting rate on the strength of an EMAIL. The
# measure would have gone on being called "minutes posted" while quietly meaning
# "minutes we have somehow".
#
# A document the town posted carries its Agenda Center address; one that arrived any other
# way does not, and that is the whole test. It is also why the delivery does not flatter
# the board that made it -- which is the property this page most needs.
def posted(m):
    """Did the TOWN publish these minutes, as opposed to us holding a copy."""
    return m['minutes'] == '1' and bool(m.get('minutes_url'))



YEARS = 4                 # the fiscal years shown: the latest complete-ish one and three before
MIN_MEETINGS = 20         # a board with fewer meetings across the window is listed, not ranked
THE_THREE = ('school-committee', 'select-board', 'finance-committee')


def fail(msg):
    raise SystemExit('build_board_posting: ' + msg)


def fy_of(date):
    y = int(date[:4])
    return y + 1 if date[5:7] >= '07' else y


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def build(as_of):
    cutoff = (dt.date.fromisoformat(as_of) - dt.timedelta(days=LAG_DAYS)).isoformat()
    boards = {b['slug']: b for b in json.load(open(BOARDS, encoding='utf-8'))['boards']}
    slug_by_name = {}
    for b in boards.values():
        slug_by_name[b['name']] = b['slug']
    # THE ONE MEETING RECORD, not another join. sources/data/meeting-register.csv is a row
    # per meeting with every artifact on it (build_meeting_register.py); this page reads it
    # so "the Select Board met 110 times" cannot mean one thing here and another on
    # /this-week. A hearing listed inside another board's meeting (`part_of`) is not a
    # second meeting and is left out.
    reg = [r for r in csv.DictReader(open(REGISTER, encoding='utf-8')) if not r['part_of']]
    if not reg:
        fail('no meetings in %s — run scripts/build_meeting_register.py' % os.path.relpath(REGISTER, ROOT))
    unmatched = collections.Counter()
    mt = {}
    for r in reg:
        if r['board_slug'] not in boards:
            unmatched[r['board']] += 1
            continue
        if r['date'] > cutoff or r['noticed'] != '1':
            continue
        mt[(r['board_slug'], r['date'])] = r
    if not mt:
        fail('no meetings matched a board')
    eligible_by_fy = collections.Counter(fy_of(d) for _, d in mt)
    latest_fy = max(f for f, n in eligible_by_fy.items() if n >= 100)
    fys = list(range(latest_fy - YEARS + 1, latest_fy + 1))
    recorded = {k for k, r in mt.items() if r['video'] == '1'}

    table = []
    for slug, b in boards.items():
        years = []
        for f in fys:
            ms = [(k, m) for k, m in mt.items() if k[0] == slug and fy_of(k[1]) == f]
            n = len(ms)
            years.append(dict(fy=f, meetings=n, with_minutes=sum(1 for _, m in ms if posted(m)),
                              recorded=sum(1 for k, _ in ms if k in recorded),
                              complete=round(sum(int(m['complete']) for _, m in ms) / n, 2) if n else 0))
        n = sum(y['meetings'] for y in years)
        k = sum(y['with_minutes'] for y in years)
        rec = sum(y['recorded'] for y in years)
        if n == 0:
            continue
        ms_all = [m for kk, m in mt.items() if kk[0] == slug and fy_of(kk[1]) in fys]
        comp = sum(int(m['complete']) for m in ms_all)
        table.append(dict(slug=slug, name=b['name'], the_three=slug in THE_THREE, years=years,
                          meetings=n, with_minutes=k, share=round(100 * k / n, 1),
                          recorded=rec, recorded_share=round(100 * rec / n, 1),
                          # HOW COMPLETE THE RECORD IS, the same seven parts the meeting
                          # record counts. A board that is never recorded loses a seventh
                          # of its score, and that is the intent: TJ, 18 September 2026,
                          # "that's still a gap compared to other boards. and it's an
                          # ok/accepted gap, but still a gap."
                          complete=round(100 * comp / (7 * len(ms_all)), 1) if ms_all else 0,
                          captions_disabled=b['counts'].get('captions_disabled', 0),
                          ranked=n >= MIN_MEETINGS))
    table.sort(key=lambda r: (-r['share'], r['name']))
    ranked = [r for r in table if r['ranked']]
    for i, r in enumerate(ranked):
        r['rank'] = i + 1
    total_n = sum(r['meetings'] for r in table)
    total_k = sum(r['with_minutes'] for r in table)

    def row(slug):
        return next(r for r in table if r['slug'] == slug)
    sc, sb, fc = row('school-committee'), row('select-board'), row('finance-committee')
    best = ranked[0]
    # The biggest FALL between the first and last shown year, among ranked boards with
    # at least ten meetings in both years.
    def year(r, f):
        return next(y for y in r['years'] if y['fy'] == f)
    falls = []
    for r in ranked:
        a, z = year(r, fys[0]), year(r, fys[-1])
        if a['meetings'] >= 10 and z['meetings'] >= 10:
            falls.append((100 * a['with_minutes'] / a['meetings'] - 100 * z['with_minutes'] / z['meetings'], r, a, z))
    falls.sort(key=lambda x: -x[0])
    fall_pts, fall_r, fall_a, fall_z = falls[0]
    sc_years = [year(sc, f) for f in fys]
    sc_zero = [y for y in sc_years if y['meetings'] >= 10 and y['with_minutes'] == 0]
    sc_last = sc_years[-1]
    sc_since = [y for y in sc_years if y not in sc_zero]
    sc_since_n = sum(y['meetings'] for y in sc_since)
    sc_since_k = sum(y['with_minutes'] for y in sc_since)

    rows_out = [
        conclusion(
            id='the-standard',
            claim='The %s: minutes posted for %s of %s meetings, the best of any board.'
                  % (best['name'], C.num(best['with_minutes']), C.num(best['meetings'])),
            so_what='What posting every meeting’s minutes looks like on the town’s site; every other board is measured against it.',
            figures={'share': figure(best['share'], C.pct(best['share']), 'of the %s’s meetings have posted minutes' % best['name']),
                     'k': figure(best['with_minutes'], C.num(best['with_minutes'])), 'n': figure(best['meetings'], C.num(best['meetings'])),
                     'fy0': figure(fys[0], 'FY%d' % fys[0]), 'fy1': figure(fys[-1], 'FY%d' % fys[-1]),
                     'all_k': figure(total_k, C.num(total_k)), 'all_n': figure(total_n, C.num(total_n)),
                     'all_share': figure(100 * total_k / total_n, C.pct(100 * total_k / total_n, 0)),
                     'boards': figure(len(ranked), C.num(len(ranked)))},
            figure='share', kind='measured', bearing='sizes',
            detail='Across all %s boards with twenty or more meetings, FY%d to FY%d, %s of %s meetings have minutes posted, %s. '
                   'The %s posted minutes for %s of %s of its own — %s — over the same four years.'
                   % (C.num(len(ranked)), fys[0], fys[-1], C.num(total_k), C.num(total_n), C.pct(100 * total_k / total_n, 0),
                      best['name'], C.num(best['with_minutes']), C.num(best['meetings']), C.pct(best['share'])),
            basis='The town’s Agenda Center, every agenda and every set of minutes it lists per board (sources/meetings/index.csv). '
                  'A meeting is a date with a posted agenda; it has minutes if minutes are listed for the same board and date. '
                  'Meetings in the last %d days are left out, because minutes are approved at the next meeting and posted after.' % LAG_DAYS,
            not_shown='Whether a meeting was held. A posted agenda for a cancelled meeting counts as a meeting without minutes, and the Agenda Center does not mark cancellations.',
            see=[('/boards', 'Every board, one page each')],
        ),
        conclusion(
            id='school-committee-by-year',
            claim='The School Committee posted minutes for %s of its FY%d meetings (%s of %s); none in FY%d.'
                  % (C.pct(100 * sc_last['with_minutes'] / sc_last['meetings'], 0), sc_last['fy'], C.num(sc_last['with_minutes']), C.num(sc_last['meetings']),
                     sc_zero[0]['fy'] if sc_zero else fys[0]),
            so_what='Its four-year figure, %s, is mostly one blank year; since then it runs %s. The standard above is %s.' % (C.pct(sc['share'], 0), C.pct(100 * sc_since_k / sc_since_n, 0), C.pct(best['share'], 0)),
            figures={'last_share': figure(100 * sc_last['with_minutes'] / sc_last['meetings'], C.pct(100 * sc_last['with_minutes'] / sc_last['meetings'], 0),
                                          'of School Committee meetings with minutes posted, FY%d' % sc_last['fy']),
                     'last_k': figure(sc_last['with_minutes'], C.num(sc_last['with_minutes'])), 'last_n': figure(sc_last['meetings'], C.num(sc_last['meetings'])),
                     'last_fy': figure(sc_last['fy'], 'FY%d' % sc_last['fy']),
                     'zero_fy': figure(sc_zero[0]['fy'] if sc_zero else fys[0], 'FY%d' % (sc_zero[0]['fy'] if sc_zero else fys[0])),
                     'zero_n': figure(sc_zero[0]['meetings'] if sc_zero else sc_years[0]['meetings'], C.num(sc_zero[0]['meetings'] if sc_zero else sc_years[0]['meetings'])),
                     'four': figure(sc['share'], C.pct(sc['share'], 0)), 'best_share': figure(best['share'], C.pct(best['share'], 0)),
                     'since_k': figure(sc_since_k, C.num(sc_since_k)), 'since_n': figure(sc_since_n, C.num(sc_since_n)),
                     'since_share': figure(100 * sc_since_k / sc_since_n, C.pct(100 * sc_since_k / sc_since_n, 0)),
                     'rank': figure(sc['rank'], C.num(sc['rank'])), 'boards': figure(len(ranked), C.num(len(ranked))),
                     **{'y%d_k' % y['fy']: figure(y['with_minutes'], C.num(y['with_minutes'])) for y in sc_years},
                     **{'y%d_n' % y['fy']: figure(y['meetings'], C.num(y['meetings'])) for y in sc_years},
                     **{'y%d' % y['fy']: figure(y['fy'], 'FY%d' % y['fy']) for y in sc_years}},
            figure='last_share', kind='measured', bearing='lever',
            detail='Year by year: %s. Leaving out the blank year, %s of %s meetings have minutes, %s. Over all four years the committee ranks %s of %s boards.'
                   % ('; '.join('FY%d %s of %s' % (y['fy'], C.num(y['with_minutes']), C.num(y['meetings'])) for y in sc_years),
                      C.num(sc_since_k), C.num(sc_since_n), C.pct(100 * sc_since_k / sc_since_n, 0), C.num(sc['rank']), C.num(len(ranked))),
            basis='The same count, School Committee rows only. The district’s own site sends readers to the town’s Agenda Center for its minutes (checked 17 September 2026), so this is the shelf to count.',
            not_shown='Why. A vacancy, a policy, minutes approved and never uploaded — nothing in the Agenda Center distinguishes them, and this page does not guess.',
            see=[('/boards/school-committee', 'The School Committee’s page')],
        ),
        conclusion(
            id='the-biggest-fall',
            claim='The %s went from %s of meetings with minutes in FY%d to %s in FY%d.'
                  % (fall_r['name'], C.pct(100 * fall_a['with_minutes'] / fall_a['meetings'], 0), fall_a['fy'],
                     C.pct(100 * fall_z['with_minutes'] / fall_z['meetings'], 0), fall_z['fy']),
            so_what='The largest fall of any board over the four years, %s points. A lifetime average would not show it.' % C.num(round(fall_pts)),
            figures={'fall': figure(fall_pts, C.num(round(fall_pts)), 'points, FY%d to FY%d' % (fall_a['fy'], fall_z['fy'])),
                     'a_share': figure(100 * fall_a['with_minutes'] / fall_a['meetings'], C.pct(100 * fall_a['with_minutes'] / fall_a['meetings'], 0)),
                     'z_share': figure(100 * fall_z['with_minutes'] / fall_z['meetings'], C.pct(100 * fall_z['with_minutes'] / fall_z['meetings'], 0)),
                     'a_fy': figure(fall_a['fy'], 'FY%d' % fall_a['fy']), 'z_fy': figure(fall_z['fy'], 'FY%d' % fall_z['fy']),
                     'a_k': figure(fall_a['with_minutes'], C.num(fall_a['with_minutes'])), 'a_n': figure(fall_a['meetings'], C.num(fall_a['meetings'])),
                     'z_k': figure(fall_z['with_minutes'], C.num(fall_z['with_minutes'])), 'z_n': figure(fall_z['meetings'], C.num(fall_z['meetings'])),
                     'lag': figure(LAG_DAYS, C.num(LAG_DAYS))},
            figure='fall', kind='measured', bearing='sizes',
            detail='%s of %s meetings in FY%d had minutes; %s of %s in FY%d. Meetings in the last %d days are already excluded, so this is not the posting lag.'
                   % (C.num(fall_a['with_minutes']), C.num(fall_a['meetings']), fall_a['fy'], C.num(fall_z['with_minutes']), C.num(fall_z['meetings']), fall_z['fy'], LAG_DAYS),
            basis='The same count, first and last fiscal year in the window, boards with ten or more meetings in both.',
            not_shown='Whether minutes exist and were not posted, or were never written. The Agenda Center shows what was uploaded.',
            see=[('/boards/' + fall_r['slug'], 'The %s’s page' % fall_r['name'])],
        ),
    ]
    return dict(
        generated_by='scripts/build_board_posting.py',
        about='How the boards post: for every board the town posts for, the share of its meetings that got minutes, by fiscal year, and how many were recorded.',
        grain='COUNTS of documents on the town’s Agenda Center — a meeting is a date with a posted agenda; minutes are minutes listed for that date. Not whether a meeting happened, and not what the minutes say.',
        as_of=as_of, lag_days=LAG_DAYS, fys=fys, min_meetings=MIN_MEETINGS,
        totals=dict(meetings=total_n, with_minutes=total_k, share=round(100 * total_k / total_n, 1), boards_ranked=len(ranked)),
        boards=table,
        unmatched=[dict(board=b, documents=n) for b, n in unmatched.most_common()],
        # WHAT THE BOARD ITSELF SAYS ABOUT ITS OWN NUMBER. The Chair of the Select Board
        # sent sixteen sets of minutes the town had never posted, seven of them approved
        # at one meeting on 15 September 2026 and seven still in draft. This page is not
        # an audit (rule 8), and a board that answers the measure by producing the missing
        # documents has done the thing the measure is for -- so its account belongs beside
        # the figure rather than in a footnote. It is a STATEMENT, attributed, and it does
        # not move the measure: these did not go on the Agenda Center, which is what this
        # page counts.
        delivered=dict(
            who='the Chair of the Select Board',
            when='18 September 2026',
            n=16, approved=9, draft=7,
            approved_at='15 September 2026',
            earliest='2024-08-13', latest='2025-11-17',
            what='Sixteen sets of Select Board minutes the town had not published, sent '
                 'to this project after a question about the gap. Nine are approved, '
                 'seven of them at the Board\u2019s meeting of 15 September 2026; seven '
                 'are still drafts the Board has not voted on.',
            why_unchanged='The figure above is unchanged, and should be: it counts minutes '
                          'the town POSTED on its Agenda Center, and these arrived by '
                          'email. They are now in this archive and searchable, which is a '
                          'different thing from being published by the town.',
            provenance='sources/meetings/PROVENANCE-select-board-2026-09-18.md'),
        not_established=[
            'How long after a meeting its minutes appear. The watcher has recorded posting dates only since 8 September 2026; a year of it will say.',
            'Whether an agenda without minutes was a meeting that happened. The Agenda Center does not mark cancellations.',
            'Whether every recording is of the meeting the agenda names; recordings are classified to a board and date by title.',
            'Whether minutes a board holds but has not posted exist for any other board. '
            'Sixteen turned up for the Select Board because somebody was asked; nothing '
            'here samples the other thirty-eight, and a board with no posted minutes may '
            'have written them.',
        ],
        conclusions=emit('boardcompare', rows_out),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check and os.path.exists(OUT):
        a.as_of = json.load(open(OUT, encoding='utf-8')).get('as_of', a.as_of)
    data = build(a.as_of)
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_board_posting.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the meetings index' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    t = data['totals']
    print('%s: %d boards, %s of %s meetings with minutes (%s%%), FY%d–FY%d; %d conclusions'
          % (os.path.relpath(OUT, ROOT), len(data['boards']), t['with_minutes'], t['meetings'], t['share'], data['fys'][0], data['fys'][-1], len(data['conclusions'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
