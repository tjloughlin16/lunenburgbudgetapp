#!/usr/bin/env python3
"""The town's meeting feed: what is coming, and what has just been posted.

    python3 scripts/build_meeting_feed.py            # write fy28/public/data/meeting-feed.json
    python3 scripts/build_meeting_feed.py --check    # fail if it is stale

THIS IS AN ANNOUNCEMENT, NOT A MEASUREMENT, AND THE PAYLOAD SAYS SO

Every other JSON this project publishes is a figure checkable against a document. This one
is what our crawler could see on the town's website on a given day. The two must not be
read as the same kind of number -- a wrong meeting date is a small error, and a wrong
meeting date sitting beside a budget figure teaches a reader that the budget figures are
that kind of number. So the payload leads with `category: "announcement"` and carries the
caveat in the object rather than only on a page, because a JSON endpoint is read by
programs that never see the page.

NO WALL CLOCK. THAT IS WHAT MAKES IT REPRODUCE

"Upcoming" is relative to `as_of`, and `as_of` is THE DATE OF THE LAST LIVE CRAWL, read out
of the run log -- not today. If it were today this file would be stale by definition every
midnight and `--check` would be a nuisance alarm rather than a signal. The consequence is
that the feed states the day it was checked and goes visibly out of date instead of
silently doing so, which is the honest failure.

WHAT `first_seen` MEANS (rule 7, and it is the whole caveat)

The AgendaCenter publishes no posting timestamp. `first_seen` is the day OUR crawler first
saw a document, so the gap between a meeting and its minutes appearing is an UPPER BOUND on
how long the town took, not a measurement of it. Every such field is named
`*_upper_bound`. Documents adopted when the watch was seeded have no `first_seen` at all
and are excluded from every lag figure rather than given a default.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
STATE = os.path.join(DATA, 'meeting-watch-state.csv')
EVENTS = os.path.join(DATA, 'meeting-watch-events.csv')
RUNS = os.path.join(DATA, 'meeting-watch-runs.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'meeting-feed.json')

# How far back "awaiting minutes" looks. A meeting from 2011 with no minutes is a fact
# about the record, which is what minutes-coverage.csv is for; this surface is about
# whether the town is keeping up NOW.
AWAITING_WINDOW_DAYS = 365
UPCOMING_HORIZON_DAYS = 28


def rows(path):
    if not os.path.exists(path):
        raise SystemExit('%s is absent. Run scripts/watch_meetings.py --seed first.'
                         % os.path.relpath(path, ROOT))
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def days(a, b):
    return (dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days


def build():
    state, events, runs = rows(STATE), rows(EVENTS), rows(RUNS)
    if not state:
        raise SystemExit('the watch state holds no documents. Refusing to publish an '
                         'empty feed -- an empty feed and a town that stopped meeting '
                         'look identical to a reader.')
    live = [r for r in runs if r['source'] == 'live']
    if not live:
        raise SystemExit('the run log records no LIVE crawl. A feed whose only input is '
                         'the seed has never checked anything -- refusing to write.')
    as_of = max(r['ran'] for r in live)

    # ---- the meeting identity, and the join the second surface rests on.
    # The town gives an agenda and its minutes the SAME file id, so that -- not the date --
    # is what pairs them. A board can meet twice in a day.
    minutes = {(r['board_slug'], r['date'], r['file_id'])
               for r in state if r['kind'] == 'minutes'}
    agendas = [r for r in state if r['kind'] == 'agenda']
    paired = [r for r in agendas
              if (r['board_slug'], r['date'], r['file_id']) in minutes]
    if not paired:
        raise SystemExit('not one agenda joined to a set of minutes. A join that matches '
                         'nothing looks exactly like a town that publishes no minutes -- '
                         'refusing to write.')

    upcoming = sorted(
        ({'board': r['board'], 'board_slug': r['board_slug'], 'date': r['date'],
          'days_away': days(r['date'], as_of), 'agenda_url': r['url'],
          'file_id': r['file_id']}
         for r in agendas
         if r['date'] >= as_of and days(r['date'], as_of) <= UPCOMING_HORIZON_DAYS),
        key=lambda d: (d['date'], d['board']))

    awaiting = sorted(
        ({'board': r['board'], 'board_slug': r['board_slug'], 'date': r['date'],
          'days_since_meeting': days(as_of, r['date']), 'agenda_url': r['url']}
         for r in agendas
         if r['date'] < as_of
         and 0 < days(as_of, r['date']) <= AWAITING_WINDOW_DAYS
         and (r['board_slug'], r['date'], r['file_id']) not in minutes),
        key=lambda d: d['date'], reverse=True)

    announced = sorted(
        ({'first_seen': e['first_seen'], 'board': e['board'],
          'board_slug': e['board_slug'], 'meeting_date': e['meeting_date'],
          'kind': e['kind'], 'url': e['url'],
          'days_after_meeting_upper_bound':
              int(e['days_after_meeting_upper_bound'])
              if e['days_after_meeting_upper_bound'] else None}
         for e in events),
        key=lambda d: (d['first_seen'], d['meeting_date'], d['board']), reverse=True)

    minutes_events = [e for e in announced if e['kind'] == 'minutes'
                      and e['days_after_meeting_upper_bound'] is not None]

    return {
        'category': 'announcement',
        'not_a_measurement':
            'This file records what the Lunenburg Budget Project\'s crawler could see on '
            'the town\'s AgendaCenter on the date given. It is not a figure checked '
            'against a document, and it must not be presented beside one as the same '
            'kind of number.',
        'as_of': as_of,
        'as_of_means':
            'The date of the last live crawl, not today. This feed goes visibly out of '
            'date rather than silently.',
        'first_seen_means':
            'The day our crawler first saw a document. The town publishes no posting '
            'timestamp, so a gap between a meeting and its minutes appearing is an UPPER '
            'BOUND on how long the town took, never a measurement of it. Documents '
            'adopted when the watch was seeded have no first_seen and are excluded from '
            'every lag figure.',
        'source': 'https://www.lunenburgma.gov/AgendaCenter',
        'watched': {
            'boards': len({r['board_slug'] for r in state}),
            'documents': len(state),
            'agendas': len(agendas),
            'minutes': len(minutes),
            'agendas_paired_with_minutes': len(paired),
            'seeded_without_a_first_seen_date':
                sum(1 for r in state if r['basis'] == 'seed'),
            'observed_appearing': sum(1 for r in state if r['basis'] == 'observed'),
        },
        'runs': [{'ran': r['ran'], 'source': r['source'],
                  'boards_listed': int(r['boards_listed']),
                  'documents_listed': int(r['documents_listed']),
                  'boards_unanswered': int(r['boards_unanswered'] or 0),
                  'new_agendas': int(r['new_agendas'] or 0),
                  'new_minutes': int(r['new_minutes'] or 0)}
                 for r in sorted(runs, key=lambda r: (r['ran'], r['source']),
                                 reverse=True)],
        'upcoming': {
            'horizon_days': UPCOMING_HORIZON_DAYS,
            'basis': 'an agenda posted for a date on or after as_of. An agenda is not a '
                     'guarantee the meeting happens, and a meeting can be held with no '
                     'agenda posted.',
            'count': len(upcoming),
            'next_7_days': [m for m in upcoming if m['days_away'] <= 7],
            'meetings': upcoming,
        },
        'awaiting_minutes': {
            'window_days': AWAITING_WINDOW_DAYS,
            'basis': 'an agenda posted for a past date whose file id has no minutes '
                     'alongside it in the town\'s listing. This is minutes against '
                     'AGENDAS, not against meetings held -- the same proxy '
                     'sources/data/minutes-coverage.csv rests on, and the town publishes '
                     'nothing that reconciles the two.',
            'count': len(awaiting),
            'oldest': awaiting[-1] if awaiting else None,
            'meetings': awaiting[:200],
        },
        'announced': {
            'basis': 'documents this watch saw appear between one run and the next. '
                     'Everything present when the watch was seeded is deliberately absent '
                     'here: it was already known and was never new.',
            'count': len(announced),
            'minutes_with_a_lag_bound': len(minutes_events),
            'items': announced[:200],
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    made = json.dumps(build(), indent=2, sort_keys=True) + '\n'

    if a.check:
        if not os.path.exists(OUT):
            print('STALE — %s has never been written' % os.path.relpath(OUT, ROOT))
            return 1
        if open(OUT, encoding='utf-8').read() != made:
            print('STALE — %s no longer reproduces from the meeting watch state. '
                  'Run scripts/build_meeting_feed.py.' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — the meeting feed reproduces from the watch state')
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(made)
    d = json.loads(made)
    print('wrote %s — as of %s: %d upcoming (%d in 7 days), %d awaiting minutes, '
          '%d announced'
          % (os.path.relpath(OUT, ROOT), d['as_of'], d['upcoming']['count'],
             len(d['upcoming']['next_7_days']), d['awaiting_minutes']['count'],
             d['announced']['count']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
