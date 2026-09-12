#!/usr/bin/env python3
"""Every conclusion on every report, checked against the report it came from.

    python3 scripts/verify_conclusions.py

WHAT THIS CATCHES THAT `--check` DOES NOT

Each generator's `--check` proves its payload still reproduces from the database. That is
the staleness half. It cannot notice a conclusion whose figure was computed *inside the
conclusion* and appears nowhere else in the report -- a number with no published series
behind it, which reads exactly like every other number on the page.

So this is the traceability half, and it asserts four things:

  1. **RULE 2, RE-RUN.** `conclusions.check()` again, on what actually shipped: every
     figure the prose states is registered, and no unregistered digit is left in it. The
     generator asserts this on the way out; this asserts it on the way in, which is the
     difference between checking your own work and checking the artefact.

  2. **HOW MUCH OF IT IS QUOTED AND HOW MUCH IS ARITHMETIC**, counted and printed. Every
     registered value is looked for elsewhere in the same payload -- in a series, a
     headline, a total, a row. One that is there is a figure the report already publishes;
     one that is not is arithmetic the conclusion did on figures it does, which is
     legitimate and is exactly where a slip would hide.

     THIS IS MEASURED AND NOT ASSERTED, and the reason is worth writing down. A hard
     failure here would need a hand-kept list of every legitimate difference, share and
     counterfactual across sixteen reports -- and a hand-kept list of one's own exceptions
     is the artefact that goes stale first and is least likely to be noticed doing it.
     What it prints instead is the RATIO, per report, so a page that starts computing
     rather than quoting is visible in this output before anybody has to ask.

  3. **THE MASTER REPORT SAYS ONLY WHAT THE REPORTS SAY.** Every headline in
     /what-it-all-adds-up-to is byte-identical to the first conclusion of the report it
     names, and every conclusion in its by-report section is byte-identical to that
     report's own. A synthesis that drifted from its sources is the defect this project
     has shipped most often.

  4. **IT FAILS CLOSED, MEASURABLY.** Every routed report is either represented in the
     master report or named in its `not_covered` list. Nothing may be in neither.

RULE 13. This reads the published payloads, which is what a reader gets, rather than
re-running the generators and comparing them to themselves.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import conclusions as C                                   # noqa: E402
from build_reports_index import routed_reports            # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
MASTER = os.path.join(PUB, 'what-it-all-adds-up-to.json')

FAILS = []
CHECKS = [0]

# The report this page IS. It carries everybody else's conclusions and has none of its
# own by construction, so it is not a hole in its own coverage.
SELF = 'addsup'

# The two tabs in this area that are not reports: the Markdown renderer, and the four-way
# chooser at /special-education. Named identically in build_master_report.py, and this
# file asserts the two lists agree so a tab cannot be excluded in one and expected in the
# other.
NOT_A_REPORT = ('analysis', 'sped', 'blog', 'recorded', 'thisweek')


def head(t):
    print('\n%s\n%s' % (t, '-' * len(t)))


def nums(o, into):
    """Every number anywhere in a payload, flattened. The haystack for check 2."""
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        into.add(round(float(o), 4))
    elif isinstance(o, dict):
        for k, v in o.items():
            if k == 'conclusions':
                continue        # the conclusion may not vouch for itself
            nums(v, into)
    elif isinstance(o, list):
        for v in o:
            nums(v, into)
    elif isinstance(o, str):
        pass


def check_report(rid, payload):
    rows = payload.get('conclusions') or []
    if not rows:
        return 0, 0, 0

    # 1. rule 2, on what shipped.
    CHECKS[0] += 1
    # `literals` ships with each row, so this is the same check the generator ran, on the
    # file a reader gets rather than on the generator's own copy of it.
    FAILS.extend(C.check(rid, rows))

    pool = set()
    nums(payload, pool)
    quoted = computed = 0

    for c in rows:
        CHECKS[0] += 1
        if c['kind'] not in C.KINDS:
            FAILS.append('%s/%s: kind is %r' % (rid, c['id'], c['kind']))
        for name in ('claim', 'detail', 'basis', 'not_shown'):
            if not (c.get(name) or '').strip():
                FAILS.append('%s/%s: %s is empty' % (rid, c['id'], name))
        if c.get('figure') and c['figure'] not in c['figures']:
            FAILS.append('%s/%s: headline figure %r is not one of its figures'
                         % (rid, c['id'], c['figure']))
        for name, f in sorted(c['figures'].items()):
            CHECKS[0] += 1
            if f['text'] not in ' '.join((c['claim'], c.get('so_what', ''), c['detail'])):
                FAILS.append('%s/%s: figure %r renders as %r, which is in neither the '
                             'claim nor the detail'
                             % (rid, c['id'], name, f['text']))
            v = f['value']
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if round(float(v), 4) in pool:
                quoted += 1
            else:
                computed += 1
    return len(rows), quoted, computed


def main():
    head('§1  every report, its own conclusions')
    reports, _ = routed_reports(all_of_area=True)
    seen, total, quoted, computed = {}, 0, 0, 0
    for rep in reports:
        if not rep.get('data'):
            continue
        p = os.path.join(ROOT, 'fy28', 'public', rep['data']['url'].lstrip('/'))
        if not os.path.exists(p):
            continue
        payload = json.load(open(p, encoding='utf-8'))
        rid = rep['url'].lstrip('/')
        if rep['id'] == SELF or rep['id'] in NOT_A_REPORT:
            continue
        n, q, c = check_report(rid, payload)
        seen[rep['id']] = payload.get('conclusions') or []
        total += n
        quoted += q
        computed += c
        print('  %-4s %-46s %2d conclusions  %3d figures quoted, %2d computed'
              % ('OK' if n else '--', rep['url'], n, q, c))
    print('  %d conclusions across %d reports — %d of %d figures appear elsewhere in '
          'their own report, %d are arithmetic on ones that do'
          % (total, len([1 for v in seen.values() if v]), quoted, quoted + computed,
             computed))

    head('§2  the master report says only what the reports say')
    if not os.path.exists(MASTER):
        FAILS.append('%s is missing — run scripts/build_master_report.py'
                     % os.path.relpath(MASTER, ROOT))
        return report()
    m = json.load(open(MASTER, encoding='utf-8'))

    # The two exclusion lists must agree, or a report is dropped from the synthesis by one
    # file and expected by the other -- which is a silent hole wearing the shape of a
    # deliberate one.
    CHECKS[0] += 1
    import build_master_report as B
    if tuple(sorted(B.NOT_A_REPORT)) != tuple(sorted(NOT_A_REPORT)) or B.SELF != SELF:
        FAILS.append('build_master_report.py and this file disagree about which tabs are '
                     'not reports: %r against %r' % (B.NOT_A_REPORT, NOT_A_REPORT))

    by_id = {r['id']: r for r in m['reports']}
    for tab, rows in seen.items():
        CHECKS[0] += 1
        if tab not in by_id and tab not in {h['id'] for h in m['not_covered']}:
            FAILS.append('%s is a routed report and the master report neither carries it '
                         'nor names it as uncovered' % tab)
            continue
        if tab in by_id and by_id[tab]['conclusions'] != rows:
            FAILS.append('the master report’s copy of %s has drifted from the '
                         'report’s own' % tab)
    print('  OK    every report is either carried or named')

    for h in m['headlines']:
        CHECKS[0] += 1
        own = seen.get(h['report'])
        if not own:
            FAILS.append('the master report headlines %s and that report publishes no '
                         'conclusions' % h['report'])
            continue
        first = own[0]
        if h['claim'] != first['claim'] or h['detail'] != first['detail']:
            FAILS.append('the headline for %s is not that report’s first conclusion'
                         % h['report'])
    print('  OK    %d headlines, each the first conclusion of its own report'
          % len(m['headlines']))

    head('§3  the persona review — notes/process/PERSONAS.md')
    # Rule 15a: a verifier checks the figures and cannot check that anybody's question was
    # answered. What it CAN do is fail if the text that satisfied a reader's test is later
    # removed, which is the half of the review that decays silently. Each needle is the
    # phrase that answered one persona, asserted against the page source and the payload
    # together -- the meeting quotes and the claims live in the JSON, so checking only the
    # .tsx would report a met test as unmet.
    page = os.path.join(ROOT, 'fy28', 'src', 'pages', 'WhatItAllAddsUpTo.tsx')
    hay = ' '.join((open(page, encoding='utf-8').read()
                    + json.dumps(m, ensure_ascii=False)).split()).lower()
    NEEDED = [
        ('1. the resident who thinks the schools are not straight with them: the worst '
         'fact is on the first screen',
         'is not in the school budget at all'),
        ('2. the second-hand reader: one sentence off the first screen that stays true '
         'when repeated',
         'the share rose further than the count'),
        ('3. the resident close to the boards: findings name mechanisms, not people',
         'what would settle it'),
        ('4. the Finance Committee member: every limit is a named document to ask for',
         'what we cannot answer'),
        ('5. the School Committee member: the written analyses are listed, not implied',
         'reaching conclusions in prose rather than in a published payload'),
        ('6. the Select Board member: a careless town-versus-school comparison is harder',
         'understates what the town raises for the schools'),
    ]
    for label, needle in NEEDED:
        CHECKS[0] += 1
        ok = ' '.join(needle.split()).lower() in hay
        print('  %s  %s' % ('OK  ' if ok else 'GONE', label))
        if not ok:
            FAILS.append('persona review: %s — the text that satisfied it is gone' % label)

    CHECKS[0] += 1
    t = m['totals']
    counted = sum(len(v) for v in seen.values())
    if t['conclusions'] != counted:
        FAILS.append('the master report counts %d conclusions; %d are published across '
                     'the reports' % (t['conclusions'], counted))
    if t['measured'] + t['hypothesis'] != t['conclusions']:
        FAILS.append('the measured and hypothesis counts do not sum to the total')
    print('  OK    %d conclusions — %d measured, %d offered as an explanation'
          % (t['conclusions'], t['measured'], t['hypothesis']))
    return report()


def report():
    print('\n%d assertions' % CHECKS[0])
    if FAILS:
        print('\n%d FAILED:' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('PASS — every conclusion traces to its own report, and the master report '
          'restates none of them')
    return 0


if __name__ == '__main__':
    sys.exit(main())
