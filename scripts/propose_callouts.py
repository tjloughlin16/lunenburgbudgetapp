#!/usr/bin/env python3
"""WHAT SOMEONE SAYS NEXT -- candidate callouts for a thread, proposed for a person, never written.

    python3 scripts/propose_callouts.py                    # hot threads, and open ones with none
    python3 scripts/propose_callouts.py tc-passios-site    # one thread
    python3 scripts/propose_callouts.py --all              # every open thread

TJ, 19 October 2026: *"if someone walked up to me and said 'did you hear about TC Passios?!'
what will they say next? 'Theres an article to vote for its demolition, that'll cost 1-4
million!'"* The kinds are his: money, a warrant article at Town Meeting, a fee and its amount,
a change to town or school services, or something otherwise impactful.

WHY IT ONLY PROPOSES. Which figure is the stake is judgement: the newest figure on the town
offices thread is a basement slab, and the stake is the $21M plan voters rejected. So this
ranks and prints; a person writes the row into sources/data/thread-callouts.csv, and
build_threads.py refuses any row whose quote is not in its source.

It reads the thread payload (fy28/public/data/threads.json), so run build_threads.py first.
Money is ranked by the largest figure heard, then recency; the rest by recency. Figures here
are as our notes heard them -- a finding aid. Go to the source before writing a row.
"""
import argparse
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREADS = os.path.join(ROOT, 'fy28', 'public', 'data', 'threads.json')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')

KINDS = [
    ('warrant', r'\b(warrant|article \w+|town meeting|ballot|debt exclusion|override|non-binding)\b'),
    ('fee',     r'\bfees?\b|\brates?\b|\bsurcharge\b|\btuition\b'),
    ('service', r'\b(eliminat\w+|cut|reduc\w+|restor\w+|clos(e|ed|ing|ure)|hours|positions?|FTE|layoffs?|program(me)?s?)\b'),
    ('money',   r'\$|\bmillion\b|\bthousand\b'),
]
WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
         'nine': 9, 'ten': 10, 'a': 1, 'half a': .5}


def magnitude(figs):
    """The largest amount a list of heard figures names, in dollars; 0 when none parses."""
    best = 0
    for f in figs:
        s = f.lower().replace(',', '')
        for n, unit in re.findall(r'(\d+(?:\.\d+)?)\s*(million|m\b|thousand|k\b)?', s):
            v = float(n) * {'million': 1e6, 'm': 1e6, 'thousand': 1e3, 'k': 1e3}.get(unit, 1)
            best = max(best, v)
        for w, v in WORDS.items():
            if re.search(r'\b%s million\b' % w, s):
                best = max(best, v * 1e6)
    return best


def heard_figures():
    """{(board, date, t): figures_as_heard} from every recording's notes."""
    out = {}
    for f in glob.glob(os.path.join(MINUTES, '*', '*.json')):
        j = json.load(open(f, encoding='utf-8'))
        for b in (j.get('minutes') or {}).get('budget_items') or []:
            out[(j['board_slug'], j['meeting_date'][:10], b.get('t'))] = b.get('figures_as_heard') or []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('thread', nargs='?')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--top', type=int, default=4)
    a = ap.parse_args()
    d = json.load(open(THREADS, encoding='utf-8'))
    figs = heard_figures()
    if a.thread:
        pick = [t for t in d['threads'] if t['id'] == a.thread]
        if not pick:
            raise SystemExit('no thread %r' % a.thread)
    else:
        pick = [t for t in d['threads'] if t['status'] == 'open'
                and (a.all or t.get('hot') or not t.get('callouts'))]
    for t in pick:
        have = ['%s %s' % (c['kind'], c['value']) for c in t.get('callouts') or []]
        print('\n== %s -- %s' % (t['id'], t['label']))
        print('   has: %s' % ('; '.join(have) or 'no callouts'))
        for kind, rx in KINDS:
            rows = []
            for c in t['chronology']:
                for i in c['items']:
                    text = i['text'] + ' ' + (i.get('quote') or '')
                    if not re.search(rx, text, re.I):
                        continue
                    if kind == 'warrant' and i['kind'] not in ('vote', 'decision', 'topic'):
                        continue
                    if kind == 'money' and i['kind'] != 'budget':
                        continue
                    f = figs.get((c['board_slug'], c['date'], i.get('t')), [])
                    rows.append((magnitude(f) if kind == 'money' else 0, c['date'], c, i, f))
            rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
            if not rows:
                continue
            print('   %s' % kind.upper())
            for _, date, c, i, f in rows[:a.top]:
                at = ' t=%s' % i['t'] if i.get('t') is not None else ''
                print('     %s %s%s [%s, %s]' % (date, c['board_slug'], at, i['kind'], i['source']))
                print('       %s' % i['text'][:160])
                if f:
                    print('       heard: %s' % ' | '.join(f[:4]))


if __name__ == '__main__':
    main()
