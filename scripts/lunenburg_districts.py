"""LUNENBURG'S SCHOOL DISTRICTS -- BOTH OF THEM -- named once.

Lunenburg's children are schooled by two public districts its taxpayers fund: its own,
Lunenburg Public Schools, and Montachusett Regional Vocational Technical ("Monty Tech"), the
regional vocational district it belongs to with the other member towns and pays an
assessment into.

WHY THIS FILE EXISTS. TJ, 23 October 2026, asking why Monty Tech was missing from the grants
comparison: the comparison sets on this site are lists of TOWNS -- the towns Lunenburg
borders (computed from boundary polygons), the peers this project chose, the towns the math
matches -- each mapped to the district that schools it. A list of towns mapped to districts
can never contain Lunenburg's own regional vocational district, because it is not any town's
district: it is eighteen towns' district. So every page that compares Lunenburg's SCHOOL data
through those sets has to make a decision about Monty Tech, and the decision is the same
everywhere: show it beside Lunenburg as its own labelled row, never counted in a median, rank
or count of the comparison; or, where a chart cannot carry it, say in one line that it is not
in the comparison and why.

WHAT IS TYPED HERE, AND WHY ONLY THIS. The two LEA codes are DESE's keys for the two
districts -- a district NAME is a rendering, the LEA is the key. They were typed in nine
scripts before this file; they are typed here and imported everywhere else. Everything else
is READ: each district's name and grade span off DESE's own grades-served file, and the member
towns off the apportionment sheet the district reprints (build_monty_tech.member_towns(), the
one parser of it).
"""
import functools
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LUNENBURG_LEA = '01620000'   # Lunenburg Public Schools
MONTY_LEA = '08320000'       # Montachusett Regional Vocational Technical

# DESE's own file of grades served by every school, by school year. The same file
# build_town_comparison.k12_districts() reads to decide which districts run a K-12 system.
SPANS = os.path.join(ROOT, 'sources', 'state-dese', 'i5up-aez6-grades-served.json')

MONTY_HREF = '/monty-tech'
MONTY_SHORT = 'Monty Tech'
MONTY_ROLE = 'Lunenburg’s vocational district (shared by member towns)'


def _fail(msg):
    raise SystemExit('lunenburg_districts: ' + msg)


@functools.lru_cache(maxsize=None)
def _spans():
    """{lea: (dese name, lowest grade, highest grade)} for the latest school year DESE prints
    each district in. Grades as DESE writes them: PK, K, 01..12."""
    if not os.path.exists(SPANS):
        _fail('%s is not on disk; run scripts/sync_archive.py --pull'
              % os.path.relpath(SPANS, ROOT))
    order = ['PK', 'K'] + ['%02d' % g for g in range(1, 13)]
    raw = json.load(open(SPANS, encoding='utf-8'))
    out = {}
    for lea in (LUNENBURG_LEA, MONTY_LEA):
        rs = [r for r in raw if r.get('dist_code') == lea and r.get('grades_served')]
        if not rs:
            _fail('LEA %s is in no row of %s' % (lea, os.path.basename(SPANS)))
        sy = max(r['sy'] for r in rs)
        rs = [r for r in rs if r['sy'] == sy]
        names = {r['dist_name'] for r in rs}
        if len(names) != 1:
            _fail('LEA %s carries %d names in SY%s: %s' % (lea, len(names), sy, sorted(names)))
        grades = []
        for r in rs:
            for g in r['grades_served'].split('-'):
                g = g.strip()
                g = g.zfill(2) if g.isdigit() else g
                if g not in order:
                    _fail('LEA %s: grade %r is not one DESE uses' % (lea, g))
                grades.append(order.index(g))
        lo, hi = order[min(grades)], order[max(grades)]
        out[lea] = (names.pop(), lo, hi, sy)
    return out


def dese_name(lea):
    """The district's name exactly as DESE prints it -- the key the town-named DESE files
    (er3w-dyti, the profiles extracts) use."""
    return _spans()[lea][0]


def grade_span(lea):
    """'9–12' for Monty Tech, 'PK–12' for Lunenburg: read, not typed."""
    _, lo, hi, _ = _spans()[lea]
    return '%s–%s' % (lo.lstrip('0') or '0', hi.lstrip('0'))


@functools.lru_cache(maxsize=None)
def monty_members():
    """The member towns, off the apportionment sheet -- the one parser of it."""
    import build_monty_tech
    m = build_monty_tech.member_towns()
    towns = sorted(t['town'] for t in m['towns'])
    if 'Lunenburg' not in towns or len(towns) != m['count']:
        _fail('the Monty Tech member table no longer lists Lunenburg among %d towns' % m['count'])
    return dict(towns=towns, count=m['count'], docs_url=m['docs_url'])


def districts():
    """Lunenburg's two districts, for a payload. Monty Tech is labelled for what it IS to
    Lunenburg, and is never a member of any comparison set."""
    mm = monty_members()
    return [
        dict(lea=LUNENBURG_LEA, dese_name=dese_name(LUNENBURG_LEA), short='Lunenburg',
             role='Lunenburg Public Schools', grades=grade_span(LUNENBURG_LEA),
             in_comparison=True),
        dict(lea=MONTY_LEA, dese_name=dese_name(MONTY_LEA), short=MONTY_SHORT,
             role=MONTY_ROLE, grades=grade_span(MONTY_LEA), members=mm['count'],
             members_docs=mm['docs_url'], href=MONTY_HREF, in_comparison=False),
    ]


def not_in_comparison(md=True):
    """THE ONE LINE a page puts beside a school comparison Monty Tech cannot sit in.

    Rule 7: everything in it is a fact read off a file -- the grade span off DESE's, the member
    count off the apportionment sheet. It says WHY it is absent (a grades 9-12 vocational
    school is not like-for-like with a K-12 district, and it is no one town's district) and
    where it IS compared, against other vocational districts."""
    link = ('[the Monty Tech pages](%s)' % MONTY_HREF) if md else MONTY_HREF
    return ('%s, Lunenburg’s vocational district (shared by its %d member towns), is not in '
            'this comparison: it teaches grades %s only and is no one town’s district, so '
            'it is set beside other vocational districts on %s.'
            % (MONTY_SHORT, monty_members()['count'], grade_span(MONTY_LEA), link))


def topic_step():
    """The same line, as a topic conclusion's note: brief.step(**topic_step()).

    A topic chart's note is capped at 160 characters and already carries its own basis, so the
    line goes under the conclusion that makes the comparison, with a real link to /monty-tech.
    Its digits are registered (rule 2, enforced by brief.check_unit): the member count is a
    figure read off the apportionment sheet, the grade span a literal read off DESE's file."""
    from conclusions import figure
    n = monty_members()['count']
    span = grade_span(MONTY_LEA)
    return dict(
        text=('Not in this comparison: %s, Lunenburg’s grades %s vocational district, shared '
              'by %d member towns. Its pupils and spending are its own, set beside other '
              'vocational districts.' % (MONTY_SHORT, span, n)),
        kind='measured', figures={'n': figure(n, '%d' % n, 'towns')}, allow=(span,),
        cite=(MONTY_HREF, MONTY_SHORT))


def assert_excluded(names, what):
    """Refuse to publish a comparison that has quietly counted Monty Tech. `names` are the
    district or town names a median, rank or count was taken over."""
    bad = {dese_name(MONTY_LEA), MONTY_SHORT} & set(names)
    if bad:
        _fail('%s counts %s; Monty Tech is shown beside a comparison, never inside one'
              % (what, sorted(bad)))


if __name__ == '__main__':
    for d in districts():
        print(d)
    print(not_in_comparison())
