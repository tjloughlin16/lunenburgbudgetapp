"""Priority-ordered cut cascade.

Each year the district must close that year's gap. Programs are cut from the bottom of
the priority ranking upward. A cut permanently reduces the salary base, so it also
lowers every later year's level-service cost -- which is why early cuts compound.
"""
import sys, json
sys.path.insert(0, 'model')
from catalog import PROGRAMS, CATEGORIES
from finance import project, DEFAULT_ASSUMPTIONS, FY27

# Category rankings. Lower number = higher priority = protected longest.
PRESETS = {
    'school_committee': {   # revealed by the Restoration->Core->LS->Balanced sequence
        'name': "School Committee's revealed priorities",
        'why': "The order Lunenburg itself sacrificed things across its own four FY27 "
               "scenarios. Athletics and arts went first; special education, mandated "
               "services and classroom teachers were defended longest.",
        'order': ['sped', 'core_classroom', 'literacy', 'wellness', 'leadership',
                  'advanced', 'operations', 'technology', 'activities', 'arts',
                  'athletics'],
    },
    'peer_districts': {     # what comparable MA districts actually did
        'name': "What comparable districts actually do",
        'why': "Observed sequence across Easthampton, Bridgewater-Raynham, South Hadley, "
               "Groton-Dunstable and Winchester: revenue levers and non-personnel first, "
               "then enrichment, then support staff, then classroom teachers last.",
        'order': ['sped', 'wellness', 'core_classroom', 'literacy', 'advanced',
                  'leadership', 'technology', 'operations', 'arts', 'activities',
                  'athletics'],
    },
    'our_recommendation': {
        'name': 'What we\u2019d do',
        'why': "Early literacy first, because it is the one loss that cannot be made up "
               "later. Classrooms next, because class size is what makes families leave. "
               "Athletics and arts sit at the bottom NOT because they matter least, but "
               "because they are the only things here that can pay for themselves \u2014 "
               "fund them with fees and they never reach the cut line at all.",
        'order': ['literacy', 'core_classroom', 'sped', 'wellness', 'advanced',
                  'leadership', 'technology', 'operations', 'arts', 'activities',
                  'athletics'],
    },
    'academics_first': {    # the user's hypothetical
        'name': 'Academics above all',
        'why': "Protect instruction and advanced coursework at any cost to everything "
               "else. Shows how far enrichment alone can carry you -- and where it stops.",
        'order': ['core_classroom', 'advanced', 'literacy', 'sped', 'wellness',
                  'technology', 'leadership', 'operations', 'activities', 'arts',
                  'athletics'],
    },
}

MANDATE_FLOOR = {'legal': 1000, 'contract': 100, 'discretionary': 0}


def expand(programs):
    """Repeatable programs (e.g. 'each additional teacher') become numbered instances."""
    out = []
    for p in programs:
        n = p.get('repeatable', 1)
        for i in range(n):
            q = dict(p)
            if n > 1:
                q['id'] = f"{p['id']}_{i+1}"
                q['name'] = f"{p['name'].replace(' (each 1.0)','')} #{i+1}"
            out.append(q)
    return out


def run(order, assumptions=None, years=5, include_restoring=True):
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    rank = {c: i for i, c in enumerate(order)}
    pool = [p for p in expand(PROGRAMS)
            if p['status'] == 'funded'
            or (include_restoring and p['status'] == 'restoring')]
    # cut last-priority first; within a category, cheapest-and-least-harmful first (tier)
    pool.sort(key=lambda p: (-rank.get(p['cat'], 99), p['tier'], p['cost']))

    results, cuts_by_year, applied = [], {}, []
    for i in range(years):
        proj = project(years=i + 1, assumptions=a, cuts_by_year=cuts_by_year)[-1]
        gap, taken = proj['deficit'], []
        while gap > 0 and pool:
            p = pool.pop(0)
            if p['mandate'] == 'legal':
                taken.append(dict(p, blocked=True))
                continue
            taken.append(dict(p, blocked=False))
            gap -= p['cost']
        applied += [t for t in taken if not t['blocked']]
        cuts_by_year[proj['fy']] = sum(t['cost'] for t in taken if not t['blocked'])
        results.append(dict(fy=proj['fy'], deficit=proj['deficit'],
                            level_service=proj['level_service'],
                            available=proj['available'], cuts=taken,
                            cut_total=cuts_by_year[proj['fy']],
                            unclosed=max(0, gap),
                            cum_fte=round(sum(t['fte'] for t in applied), 1)))
    return results


if __name__ == '__main__':
    key = sys.argv[1] if len(sys.argv) > 1 else 'school_committee'
    ps = PRESETS[key]
    print(f"=== {ps['name']} ===\n{ps['why']}\n")
    for y in run(ps['order']):
        print(f"FY{y['fy']}  gap ${y['deficit']:>10,}   cut ${y['cut_total']:>9,}"
              f"   cumulative FTE lost {y['cum_fte']}")
        for c in y['cuts']:
            flag = '  [BLOCKED: legally mandated]' if c['blocked'] else ''
            print(f"      - {c['name'][:58]:<58} ${c['cost']:>8,}{flag}")
        if y['unclosed'] > 0:
            print(f"      !! ${y['unclosed']:,} STILL UNCLOSED -- nothing left to cut")
        print()
