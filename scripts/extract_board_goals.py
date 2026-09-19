#!/usr/bin/env python3
"""THE GOALS THE BOARDS SET THEMSELVES, in their own words.

    python3 scripts/extract_board_goals.py
    python3 scripts/extract_board_goals.py --check

TJ, 19 September 2026: "if any boards have goals set, i want to have a stated goals section
at the top of each board... oh if we ALREADY track them as threads, then map them."

WHY THIS IS NOT TYPED BY HAND. A goal is a commitment a board made on the record, and
retyping one is the same risk as retyping a figure (rule 2). The FY26 Select Board and Town
Manager goals are a PUBLISHED DOCUMENT with a structure -- `Goal #N:` and `Objective N:` --
so they are parsed out of it and every line carries the document it came from. Where a goal
exists only in our minutes of a meeting, it is recorded as such and says so.

AND THE MAPPING IS THE POINT. Three of the Town Manager's FY26 objectives -- TC Passios,
925 Mass Ave, the Salary Administration Plan -- are threads this project found
independently, before anyone read this document. A goal that is already a thread does not
need a second progress mechanism: the thread IS the progress. `thread` names it.

WHAT THIS DOES NOT DO. It does not say whether a goal was MET. Nothing here scores the
town. An objective saying "complete the sale of 925 Mass Ave within the Fiscal Year" beside
a thread still open in September is a fact and a fact, and the reader draws the inference
-- rule 7, and the reason there is no `status` column.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'board-goals.csv')
COLS = ['board_slug', 'owner', 'fy', 'goal_no', 'goal', 'summary', 'objective_no', 'objective',
        'thread', 'basis', 'source', 'source_url', 'adopted_on', 'adopted_at', 'adopted_url', 'current']

# The published document, and who each of its two halves belongs to. Page 1 is the Select
# Board's own goals; the Town Manager's begin at the page that names them.
SB_DOC = 'sources/town-budget/text/2862-fy26-select-board-and-town-manager-goals-pdf.txt'
SB_URL = '/docs/town-budget/docs/2862-fy26-select-board-and-town-manager-goals-pdf.pdf'

GOAL = re.compile(r'^\s*Goal\s*#?\s*(\d+)\s*:?\s*(.+?)\s*$', re.I | re.M)
OBJ = re.compile(r'^\s*[•▪]?\s*Objective\s*(\d+)\s*:?\s*(.+?)\s*$', re.I | re.M)


def clean(s):
    s = re.sub(r'===PAGE \d+===', ' ', s)
    s = re.sub(r'Town of Lunenburg Select Board', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def parse_doc(path):
    """Goals and their objectives, in document order, with the owner switching where the
    document switches. A `Goal #1` appearing twice is not a duplicate -- it is the second
    owner's first goal, which is exactly how this document is laid out."""
    raw = open(os.path.join(ROOT, path), encoding='utf-8', errors='replace').read()
    # where the Town Manager's half begins
    m = re.search(r'Town\s*Manager\s*Goals|Town Manager\s*\n?\s*Goal\s*#?\s*1', raw, re.I)
    split = m.start() if m else len(raw)
    out = []
    for owner, part, off in (('the Select Board', raw[:split], 0), ('the Town Manager', raw[split:], split)):
        heads = [(g.start(), g.group(1), clean(g.group(2))) for g in GOAL.finditer(part)]
        for i, (pos, no, title) in enumerate(heads):
            end = heads[i + 1][0] if i + 1 < len(heads) else len(part)
            body = part[pos:end]
            objs = [(o.group(1), clean(o.group(2))) for o in OBJ.finditer(body)]
            # an objective's text runs to the next objective, so re-slice for the full line
            spans = [o.start() for o in OBJ.finditer(body)] + [len(body)]
            objs = []
            for k, o in enumerate(OBJ.finditer(body)):
                objs.append((o.group(1), clean(body[o.start():spans[k + 1]])
                             .split(':', 1)[-1].strip()))
            out.append({'owner': owner, 'goal_no': no, 'goal': title, 'objectives': objs})
    return out


# WHICH THREAD A GOAL IS, where one exists. Written by hand because it is a JUDGEMENT --
# "Disposition of Municipal Properties" is three threads and "FY27 Budget" is the budget
# feed, and no pattern match should be trusted to decide that. Keyed on (owner, goal_no,
# objective_no); a goal with no thread is simply absent.
MAP = {
    ('the Town Manager', '3', '1'): 'tc-passios-site',
    ('the Town Manager', '3', '2'): '925-mass-ave',
    ('the Town Manager', '2', '1'): 'sap-rewrite',
}


# OUR ONE-LINE READING OF EACH GOAL, so a collapsed row says something. The goals
# themselves are long -- one Select Board goal carries six objectives -- and a title alone
# ("Municipal Property") tells a reader nothing about what is inside.
#
# THESE SENTENCES ARE OURS AND THE PAGE SAYS SO. They summarise; they do not quote, and
# they do not judge. Expanding a row shows the board's own words, which is where any
# quoting should come from.
SUMMARY = {
    ('the Select Board', '1'): 'Build the FY27 budget with the other two boards, then decide what to recommend to Town Meeting.',
    ('the Select Board', '2'): 'Work out what to do with the town’s buildings, alongside the Building Design Committee.',
    ('the Select Board', '3'): 'Rewrite six board policies, from the financial rules to open meeting law training.',
    ('the Town Manager', '1'): 'Build FY27 with a three-year forecast, and finish the draft financial policies.',
    ('the Town Manager', '2'): 'Modernise the pay bylaw, and fix how new staff are brought in.',
    ('the Town Manager', '3'): 'Decommission part of TC Passios, sell 925 Mass Ave, and sort the tax-title properties.',
    ('the School Committee', '1'): 'Decide whether to rebuild or renovate, and how it would be paid for.',
    ('the School Committee', '2'): 'The playground and the parking at the primary school.',
    ('the School Committee', '3'): 'Run the budget to a schedule the boards agree on.',
    ('the School Committee', '4'): 'One long-term plan covering every school building.',
    ('the School Committee', '5'): 'Take the turf field forward with the rest of the capital work.',
    ('the School Committee FY27', '1'): 'A study of the parking and the playground at the primary school.',
    ('the School Committee FY27', '2'): 'Get the Turkey Hill application in to the state building authority.',
    ('the School Committee FY27', '3'): 'Hold the district’s finances to the process the boards agreed.',
}


# WHERE EACH SET WAS ADOPTED, from a vote in our minutes. TJ: "we always need a link to
# the meeting where the goals were set by the board."
#
# AND WHICH SET IS CURRENT, which is how this page first got it WRONG. It shipped showing
# FY26 as though it were the standing commitment, while the record holds three FY27
# adoption votes: the Town Manager's on 14 July 2026, the Select Board's on 4 August, and
# the School Committee's three on 16 September. Publishing last year's goals as this
# year's is the same defect as a stale figure in prose, and it looks identical to being
# up to date.
ADOPTED = {
    ('select-board', 'the Select Board', '2026'):
        ('', '', ''),   # not identified in the minutes we hold — see `current`
    ('select-board', 'the Town Manager', '2026'):
        ('', '', ''),
    ('school-committee', 'the School Committee', '2026'):
        ('2025-11-05', 'the School Committee', '/meeting-minutes/school-committee/2025-11-05'),
    ('select-board', 'the Town Manager', '2027'):
        ('2026-07-14', 'the Select Board', '/meeting-minutes/select-board/2026-07-14'),
    ('select-board', 'the Select Board', '2027'):
        ('2026-08-04', 'the Select Board', '/meeting-minutes/select-board/2026-08-04'),
    ('school-committee', 'the School Committee', '2027'):
        ('2026-09-16', 'the School Committee', '/meeting-minutes/school-committee/2026-09-16'),
}
CURRENT_FY = '2027'


def build():
    rows = []
    for g in parse_doc(SB_DOC):
        for no, text in (g['objectives'] or [('', '')]):
            rows.append({
                'board_slug': 'select-board',
                'owner': g['owner'], 'fy': '2026',
                'goal_no': g['goal_no'], 'goal': g['goal'],
                'summary': SUMMARY.get((g['owner'], g['goal_no']), ''),
                'objective_no': no, 'objective': text,
                'thread': MAP.get((g['owner'], g['goal_no'], no), ''),
                'basis': 'published document',
                'source': os.path.basename(SB_DOC), 'source_url': SB_URL,
            })
    # THE SCHOOL COMMITTEE'S, which exist in OUR MINUTES and not (yet) in a document we
    # hold for this year. Recorded as one goal each, quoted from the decision, and marked
    # with a different basis so a reader can tell a published commitment from a minuted one.
    sc = ('the future of Turkey Hill', 'the primary school playground/parking project',
          'a smooth FY budget process', 'a comprehensive long-term facilities plan for all buildings',
          'pursuing the turf field alongside the other capital-planning goals')
    sc_thread = {0: 'turkey-hill-rebuild', 4: 'turf-field-study'}
    for i, g in enumerate(sc):
        rows.append({
            'board_slug': 'school-committee', 'owner': 'the School Committee', 'fy': '2026',
            'goal_no': str(i + 1), 'goal': g,
            'summary': SUMMARY.get(('the School Committee', str(i + 1)), ''),
            'objective_no': '', 'objective': '',
            'thread': sc_thread.get(i, ''),
            'basis': 'our minutes of a recording',
            'source': 'school-committee 2025-11-05: "Set five school-committee goals for the year"',
            'source_url': '/meeting-minutes/school-committee/2025-11-05',
        })
    # THE SCHOOL COMMITTEE'S CURRENT THREE, adopted 16 September 2026 by roll call. They
    # replace the five set in November 2025 -- and the committee also voted to DROP the
    # tri-board process as a goal, which is recorded because a goal withdrawn is as much a
    # statement of priorities as a goal set.
    sc27 = [('the primary school parking lot and playground study', 'kids-kingdom'),
            ('the MSBA application for Turkey Hill', 'turkey-hill-rebuild'),
            ('financial fidelity', '')]
    for i, (g, th) in enumerate(sc27):
        rows.append({
            'board_slug': 'school-committee', 'owner': 'the School Committee', 'fy': '2027',
            'goal_no': str(i + 1), 'goal': g,
            'summary': SUMMARY.get(('the School Committee FY27', str(i + 1)), ''),
            'objective_no': '', 'objective': '', 'thread': th,
            'basis': 'our minutes of a recording',
            'source': 'school-committee 2026-09-16: "Accept the three school committee goals as outlined" — passed, roll call',
            'source_url': '/meeting-minutes/school-committee/2026-09-16',
        })
    for r in rows:
        on, at, url = ADOPTED.get((r['board_slug'], r['owner'], r['fy']), ('', '', ''))
        r['adopted_on'], r['adopted_at'], r['adopted_url'] = on, at, url
        r['current'] = 'yes' if r['fy'] == CURRENT_FY else 'superseded'
    return rows


def main():
    a = argparse.ArgumentParser(); a.add_argument('--check', action='store_true')
    args = a.parse_args()
    rows = build()
    if not rows:
        raise SystemExit('REFUSING: parsed no goals — the document shape has changed')
    body = ''
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS); w.writeheader()
    for r in rows: w.writerow({c: r.get(c, '') for c in COLS})
    body = buf.getvalue()
    if args.check:
        # newline='' ON BOTH SIDES. csv.DictWriter emits \r\n; a default read translates
        # it to \n, so the comparison can never match and the check reports a clean file
        # as stale every single time. CLAUDE.md records this exact bug being found in
        # check_generated.py, and here it is again — a check that always fails is as
        # useless as one that never does, and it trains you to ignore it.
        have = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else None
        if have != body:
            raise SystemExit('STALE %s — run extract_board_goals.py' % os.path.relpath(OUT, ROOT))
        print('ok — %d goal lines reproduce' % (len(rows)))
        return
    open(OUT, 'w', encoding='utf-8', newline='').write(body)
    # the payload the board pages read: one entry per board, goals nested under their owner
    import json
    by = {}
    for r in rows:
        b = by.setdefault(r['board_slug'], {})
        key = (r['owner'], r['fy'])
        o = b.setdefault(key, {'owner': r['owner'], 'fy': r['fy'], 'basis': r['basis'],
                               'source': r['source'], 'source_url': r['source_url'],
                               'adopted_on': r['adopted_on'], 'adopted_at': r['adopted_at'],
                               'adopted_url': r['adopted_url'], 'current': r['current'],
                               'goals': []})
        g = next((x for x in o['goals'] if x['no'] == r['goal_no']), None)
        if not g:
            g = {'no': r['goal_no'], 'goal': r['goal'], 'summary': r['summary'],
                 'thread': r['thread'], 'objectives': []}
            o['goals'].append(g)
        if r['objective']:
            g['objectives'].append({'no': r['objective_no'], 'text': r['objective'], 'thread': r['thread']})
        elif r['thread']:
            g['thread'] = r['thread']
    pay = {'current_fy': CURRENT_FY,
           'about': 'The goals each board set itself, in its own words. '
                    'scripts/extract_board_goals.py. Nothing here says whether a goal was MET.',
           'boards': {k: list(v.values()) for k, v in by.items()}}
    pj = os.path.join(ROOT, 'fy28', 'public', 'data', 'board-goals.json')
    open(pj, 'w', encoding='utf-8').write(json.dumps(pay, indent=1, ensure_ascii=False) + '\n')
    print('wrote %s' % os.path.relpath(pj, ROOT))
    import collections
    c = collections.Counter((r['board_slug'], r['owner']) for r in rows)
    print('wrote %s — %d lines' % (os.path.relpath(OUT, ROOT), len(rows)))
    for k, v in c.items(): print('  %-18s %-20s %d' % (k[0], k[1], v))
    print('  mapped to a thread: %d' % sum(1 for r in rows if r['thread']))


if __name__ == '__main__':
    main()
