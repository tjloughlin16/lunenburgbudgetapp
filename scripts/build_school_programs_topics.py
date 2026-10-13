#!/usr/bin/env python3
"""School programs, split into topic pages: thirteen pages and the Programs and cuts hub.

    python3 scripts/build_school_programs_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_school_programs_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. This shelf absorbs five long reports --
/what-courses-actually-ran, /ap-exams, /cut-register, /what-stopped-being-funded and
/when-grants-end -- and reads the payload each of them is already built from. It computes
nothing it can read instead.

FIVE INSTRUMENTS, AND NONE OF THEM COUNTS CHILDREN TAUGHT. Each page says which it uses:

  DESE class size        SECTIONS that ran, by school and subject AREA -- never by course. A
                         section is what the schedule offered and what students chose, together.
  DESE AP files          CHILDREN who sat at least one exam, SITTINGS, and TESTS at each score.
  the district's lists   reductions the district NAMED in a budget document. A claim of intent
                         (rule 13a: `stated`), never a record that a post went.
  the budget books       printed lines, restated by the district. A line at zero is a fact about
                         the book, not proof a service ended (rule 11: a line is net).
  DESE End of Year       dollars by fund and function. Names no grant and no post.

RULE 7 IS THE WHOLE SHELF. An announced cut is evidence of intent; a matching move in the
state's teacher count is consistency, not proof; a fall in sections cannot separate fewer
offered from fewer chosen. Every page that could be read the other way carries the gap and the
document that would close it.

NO INDIVIDUAL IS NAMED OR IDENTIFIED. Quotations that name a person are left out even where a
payload carries them, and no single-post budget line is named.

THE INPUTS, all generated and all published:

  fy28/public/data/course-offerings.json   scripts/build_course_offerings.py
  fy28/public/data/ap.json                 scripts/build_ap.py
  fy28/public/data/cut-register.json       the cut register
  fy28/public/data/stopped-funding.json    the stopped-funding analysis
  fy28/public/data/grant-unwinding.json    the grant-unwinding analysis

Where a payload carries the same quantity twice -- a series and the conclusion built from it --
this refuses to write unless the two agree.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step as _step  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources')
HUB = 'school-programs'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_school_programs_topics.py']

# The documents a gap would be closed by. Prose, no figures; said once here so two pages
# naming the same remedy cannot drift apart.
PROGRAM_OF_STUDIES = ('the district’s Program of Studies for each year and the LHS master '
                      'schedule; both were shown to the School Committee and neither is published')
REQUESTS = ('the district’s course-request tallies for each year: what students asked for '
            'beside what ran')
POSITIONS = ('the district’s year-end position control report: filled posts by FTE, school and '
             'funding source')
GRANTS = 'the district’s grant award letters and end-of-grant reports, which name the posts'


def fail(msg):
    raise SystemExit('build_school_programs_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


# ---------------------------------------------------------------- writing helpers
# Every unit of prose is a template whose {names} are figures; the text and the figure map
# are built together so the two cannot drift.
def _fmt(s, figs):
    return s.format(**{k: (v if isinstance(v, str) else v['text']) for k, v in figs.items()})


def _split(figs, allow):
    """A plain string passed as a template value is a declared LITERAL (a date naming a
    document, say), not a figure: substituted, and added to `allow`."""
    lits = tuple(allow) + tuple(v for v in figs.values() if isinstance(v, str))
    return {k: v for k, v in figs.items() if not isinstance(v, str)}, lits


def fact(id, value, kind, label, allow=(), closes=None, **figs):
    f, lits = _split(figs, allow)
    return LD.fact(id, value, _fmt(label, figs), kind, f, lits, closes)


def gap(id, label, closes):
    return LD.fact(id, None, label, 'gap', closes=closes)


def con(text, rests, allow=(), notes=(), **figs):
    f, lits = _split(figs, allow)
    return TP.conclusion(_fmt(text, figs), rests, f, lits, notes)


def note(text, kind, allow=(), closes=None, **figs):
    f, lits = _split(figs, allow)
    lits += tuple(re.findall(r'(?:FY|SY)\d{4}', closes or ''))
    return _step(_fmt(text, figs), kind, f, lits, closes=closes)


def hcon(text, rests, allow=(), **figs):
    f, lits = _split(figs, allow)
    return LD.conclusion(_fmt(text, figs), rests, f, lits)


SY = lambda y: figure(int(y), 'SY%d' % int(y), 'school year')
FY = lambda y: figure(int(y), C.fy(y), 'fiscal year')
N = lambda v, unit=None: figure(v, C.num(v), unit)
USD = lambda v: figure(v, C.usd(v))
SHARE = lambda x, dp=1: figure(round(x * 100, 4), C.pct(x * 100, dp))   # x is a fraction
PCT = lambda x, dp=1: figure(x, C.pct(x, dp))                           # x is already a percent
D1 = lambda v, unit=None: figure(v, '%.1f' % v, unit)
D2 = lambda v, unit=None: figure(v, ('%.2f' % v).rstrip('0').rstrip('.') if v != int(v) else '%d' % v, unit)


def same(a, b, what):
    if abs(float(a) - float(b)) > 1e-4:
        fail('%s: the payload states %r in one place and %r in another' % (what, a, b))


def cfig(payload, cid, key):
    c = next((x for x in payload['conclusions'] if x['id'] == cid), None)
    if c is None:
        fail('conclusion %r is no longer in its payload' % cid)
    return c['figures'][key]['value']


def said(payload, key):
    """One quotation a payload already carries, re-checked verbatim against our copy of the
    minutes it cites. A quotation that names a person is never passed in."""
    s = next((x for x in payload['said'] if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/meetings/text/'):
        fail('quotation %r does not cite our copy of the minutes' % key)
    path = os.path.join(MINUTES, s['cite'][len('/docs/'):])
    if not os.path.exists(path):
        fail('%s is not on disk; run sync_archive.py --pull' % path)
    squash = lambda t: ' '.join(t.split())
    if squash(s['quote']) not in squash(open(path, encoding='utf-8', errors='replace').read()):
        fail('quotation %r is not verbatim in %s' % (key, s['cite']))
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s minutes, %s' % (s['board'], s['date']))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    dese = 'Massachusetts DESE'
    out = {}
    for k, (key, pub) in {
            'class-size': ('state-dese/dese-class-size.xlsx', dese),
            'enrolment': ('state-dese/dese-enrollment-by-grade.xlsx', dese),
            'teacher-data': ('state-dese/dese-teacher-data.xlsx', dese),
            'ap-part': ('state-dese/dese-ap-participation.xlsx', dese),
            'ap-perf': ('state-dese/dese-ap-performance.xlsx', dese),
            'eoyr': ('state-dese/district-expenditures-by-function.xlsx',
                     dese + ', End of Year Financial Report'),
    }.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    for k, (f, what) in {
            'p-courses': ('course-offerings.json', 'sections by school and subject, generated'),
            'p-ap': ('ap.json', 'AP participation and scores, generated'),
            'p-cuts': ('cut-register.json', 'every named cut, quoted at its page, generated'),
            'p-stopped': ('stopped-funding.json', 'every school line at zero, generated'),
            'p-grants': ('grant-unwinding.json', 'school spending by fund, generated'),
    }.items():
        if not os.path.exists(os.path.join(PUB, f)):
            fail('/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/data/' + f)
    return out, man


def build():
    CO, AP, CR, SF, GU = (load(n) for n in ('course-offerings.json', 'ap.json',
                                             'cut-register.json', 'stopped-funding.json',
                                             'grant-unwinding.json'))
    src, man = sources()
    S = lambda *names: [src[n] for n in names]
    out = {}

    def doc_sources(paths_titles):
        res = []
        for key, title in paths_titles:
            if key not in man:
                fail('%s is not in archive-manifest.csv' % key)
            res.append(dict(label='Lunenburg Public Schools — %s' % title, href='/docs/' + key))
        return res

    # ================================================================ high school sections
    hl = CO['headline']
    a, b = hl['first'], hl['last']
    win = CO['window']
    if (win['first_sy'], win['last_sy']) != (a['sy'], b['sy']):
        fail('the headline no longer spans the comparison window')
    hs = {r['sy']: r for r in CO['high_school']}
    same(hs[b['sy']]['sections'], b['sections'], 'high school sections')
    misc = CO['miscellaneous']
    same(misc['sections_last'], next(s['last'] for s in CO['high_school_subjects']
                                     if s['subj'] == 'Miscellaneous'), 'Miscellaneous sections')
    misc_share = misc['sections_last'] / b['sections']
    same(round(misc_share * 100, 1), round(cfig(CO, 'a-fifth-of-high-school-sections-have-no-'
                                               'named-subject', 'share') * 100, 1), 'misc share')
    eras = CO['eras']
    g8 = next(e for e in eras if e['span'].startswith('8'))
    e9 = next(e['span'] for e in eras if e is not g8)
    if any(e['span'] != e9 for e in eras if e is not g8):
        fail('more than two grade spans in the high school’s eras; the sections chart draws two')
    courses_gap = gap('courses-gap', 'which courses those sections were', PROGRAM_OF_STUDIES)
    out['high-school-sections'] = TP.page(
        'high-school-sections',
        _fmt('Lunenburg High ran {s1} course sections in {y1} against {s0} in {y0}, with '
             '{n1} students against {n0}.', d := dict(
                 s1=N(b['sections']), y1=SY(b['sy']), s0=N(a['sections']), y0=SY(a['sy']),
                 n1=N(b['students']), n0=N(a['students']))),
        [fact('s-last', N(b['sections'], 'course sections'), 'published',
              'sections that ran at the high school, {y}', y=SY(b['sy'])),
         fact('s-first', N(a['sections'], 'course sections'), 'published',
              'sections that ran, {y}', y=SY(a['sy'])),
         fact('n-last', N(b['students'], 'students'), 'published',
              'students at the high school, {y}', y=SY(b['sy'])),
         fact('n-first', N(a['students'], 'students'), 'published',
              'students at the high school, {y}', y=SY(a['sy'])),
         fact('avg-last', D1(b['avg'], 'students per section'), 'published',
              'average students per section, {y}', y=SY(b['sy'])),
         fact('avg-first', D1(a['avg'], 'students per section'), 'published',
              'average students per section, {y}', y=SY(a['sy'])),
         fact('misc-last', N(misc['sections_last'], 'course sections'), 'published',
              'sections DESE files as Miscellaneous, {y}', y=SY(misc['last_sy'])),
         fact('misc-first', N(misc['sections_first'], 'course sections'), 'published',
              'Miscellaneous sections, {y}', y=SY(misc['first_sy'])),
         fact('misc-avg', D1(misc['avg_last'], 'students per section'), 'published',
              'average Miscellaneous section, {y}', y=SY(misc['last_sy'])),
         courses_gap],
        [con('The high school ran {d} more sections in {y1} than in {y0}, with {m} more students.',
             ['s-last', 's-first', 'n-last', 'n-first'],
             d=N(hl['sections_change']), y1=SY(b['sy']), y0=SY(a['sy']),
             m=N(hl['students_change'])),
         con('The average section fell from {a0} students to {a1}.', ['avg-first', 'avg-last'],
             a0=D1(a['avg']), a1=D1(b['avg'])),
         con('Miscellaneous went from {m0} sections to {m1}, averaging {v} students; nothing '
             'published names them.', ['misc-first', 'misc-last', 'misc-avg'],
             m0=N(misc['sections_first']), m1=N(misc['sections_last']), v=D1(misc['avg_last']),
             notes=[note('Groups this small fit academic support, electives or directed study '
                         'alike. DESE files no course name, so nothing here separates them.',
                         'hypothesis')]),
         con('A section counts a class that ran: what the schedule offered and what students '
             'chose, together.', ['courses-gap', 's-last'],
             notes=[note('DESE files sections by subject area, never by course, so an elective '
                         'ending inside a subject whose total rose cannot be seen.', 'gap',
                         closes=PROGRAM_OF_STUDIES)])],
        table=dict(caption='Lunenburg High, sections that ran, by school year', views=[dict(
            key='years', label='All subjects', total_col=-1, kinds=['ledger'] * 3,
            columns=['Sections', 'Students', 'Average class'],
            rows=[dict(label='SY%d' % y, cells=[C.num(hs[y]['sections']), C.num(hs[y]['students']),
                                               '%.1f' % hs[y]['avg']])
                  for y in sorted(hs, reverse=True)],
            note='DESE’s class-size file. From SY%d to SY%d grade 8 was taught in the high '
                 'school building, so those years count a different school and are not compared '
                 'with the rest.' % (g8['first_sy'], g8['last_sy']))]),
        chart=TP.series('High school sections that ran', ['SY%d' % y for y in sorted(hs)], [
            TP.track('Grades %s' % e9, [hs[y]['sections'] if not g8['first_sy'] <= y <= g8['last_sy']
                                       else None for y in sorted(hs)], 'published', 'bar'),
            TP.track('Grades %s, a different school' % g8['span'],
                     [hs[y]['sections'] if g8['first_sy'] <= y <= g8['last_sy'] else None
                      for y in sorted(hs)], 'published', 'bar')], 'course sections', stacked=True,
            note='DESE’s class-size file. While grade eight sat in the building the count is of a '
                 'different school, so it is drawn apart.'),
        said=[said(CO, 'whittle'), said(CO, 'studyhalls')],
        sources=S('class-size', 'enrolment', 'p-courses'),
        finding_figures=d)

    # ================================================================ world languages
    L = CO['language']
    h0, h1 = L['high_first'], L['high_last']
    mid = {r['sy']: r for r in L['middle']}
    m_from = cfig(CO, 'the-middle-school-world-language', 'sy_first')
    m0, m1 = mid[m_from], L['middle_last']
    m_dip = cfig(CO, 'the-middle-school-world-language', 'dip')
    same(mid[m_dip]['sections'], m1['sections'], 'the middle school’s earlier low')
    after_dip = mid[m_dip + 1]
    same(cfig(CO, 'foreign-language-narrowed-on-every-instrument', 'share_last'), h1['share'],
         'high school language share')
    wl = CR['fy2026']['row']
    if 'Foreign Language' not in wl['instrument']:
        fail('the cut register’s FY2026 row is no longer the world language teacher')
    wl_fy = CR['fy2026']['district']['after_fy']
    hi_rows = {r['sy']: r for r in L['high']}
    yrs = sorted(set(hi_rows) | set(mid), reverse=True)
    lang_chart = TP.series('Share of each school taking a language', ['SY%d' % y for y in yrs[::-1]], [
        TP.track('High school', [100 * hi_rows[y]['share'] if y in hi_rows else None
                                 for y in yrs[::-1]]),
        TP.track('Middle school', [100 * mid[y]['share'] if y in mid else None
                                   for y in yrs[::-1]])], '%',
        note='DESE’s class-size file: distinct students taking a language over the school’s own '
             'count.')
    out['world-languages'] = TP.page(
        'world-languages',
        _fmt('{h1} of Lunenburg High took a language in {y1}, against {h0} in {y0}; the '
             'middle school fell further.', d := dict(
                 h1=SHARE(h1['share']), y1=SY(h1['sy']), h0=SHARE(h0['share']),
                 y0=SY(h0['sy']))),
        [fact('h-share-last', SHARE(h1['share']), 'published',
              'of the high school took a language, {y}', y=SY(h1['sy'])),
         fact('h-share-first', SHARE(h0['share']), 'published',
              'of the high school took a language, {y}', y=SY(h0['sy'])),
         fact('h-sec', N(h1['sections'], 'course sections'), 'published',
              'high school language sections, {y}; {s} in {y0}', y=SY(h1['sy']),
              s=N(h0['sections']), y0=SY(h0['sy'])),
         fact('m-share-last', SHARE(m1['share']), 'published',
              'of the middle school took a language, {y}', y=SY(m1['sy'])),
         fact('m-share-first', SHARE(m0['share']), 'published',
              'of the middle school took a language, {y}', y=SY(m0['sy'])),
         fact('m-sec', N(m1['sections'], 'course sections'), 'published',
              'middle school language sections, {y}; {s} in {y0}', y=SY(m1['sy']),
              s=N(m0['sections']), y0=SY(m0['sy'])),
         fact('wl-fte', D1(wl['after'], 'full-time equivalents'), 'published',
              'language FTE, middle and high, {y}; {b} before', y=FY(wl_fy),
              b=D1(wl['before'])),
         gap('access-gap', 'whether a child who asked for a language got one', REQUESTS)],
        [con('At the high school the share fell from {a} to {b}, in {s1} sections rather than {s0}.',
             ['h-share-first', 'h-share-last', 'h-sec'],
             a=SHARE(h0['share']), b=SHARE(h1['share']), s1=N(h1['sections']),
             s0=N(h0['sections'])),
         con('At the middle school it fell from {a} in {y0} to {b} in {y1}, in {s} sections.',
             ['m-share-first', 'm-share-last', 'm-sec'],
             a=SHARE(m0['share']), y0=SY(m0['sy']), b=SHARE(m1['share']), y1=SY(m1['sy']),
             s=N(m1['sections']),
             notes=[note('The middle school also ran {s} sections in {y} and {r} the next year, '
                         'so one low year is not a subject ending. This low has now held for '
                         'two years.', 'hypothesis', s=N(mid[m_dip]['sections']), y=SY(m_dip),
                         r=N(after_dip['sections']))]),
         con('The district approved cutting a world language teacher for {y}; the state’s count '
             'fell from {b} FTE to {c}.', ['wl-fte'], y=FY(wl_fy), b=D1(wl['before']),
             c=D1(wl['after']),
             notes=[note('A matching move is consistency, not proof: a retirement in the same '
                         'subject was announced the same month.', 'hypothesis')]),
         con('Fewer sections cannot separate fewer offered from fewer chosen.', ['access-gap'],
             notes=[note('The High School Principal told the School Committee that courses are '
                         'whittled away once student choices are entered.', 'gap',
                         closes=REQUESTS)])],
        table=dict(caption='World language sections and share of each school taking one',
                   views=[dict(
            key='years', label='By school year', total_col=-1, kinds=['ledger'] * 4,
            columns=['High: sections', 'High: share', 'Middle: sections', 'Middle: share'],
            rows=[dict(label='SY%d' % y, cells=[
                C.num(hi_rows[y]['sections']) if y in hi_rows else None,
                C.pct(hi_rows[y]['share'] * 100) if y in hi_rows else None,
                C.num(mid[y]['sections']) if y in mid else None,
                C.pct(mid[y]['share'] * 100) if y in mid else None]) for y in yrs],
            note='DESE’s class-size file, Foreign Language. A share is distinct students taking '
                 'one over the school’s own count. A section is a class that ran.')]),
        chart=lang_chart,
        said=[said(CO, 'largest31'), said(CO, 'french'), said(CO, 'restoration')],
        sources=S('class-size', 'teacher-data', 'p-courses', 'p-cuts'),
        finding_figures=d)

    # ================================================================ history courses
    hist = next(s for s in CO['era_series']['subjects'] if s['subj'] == 'History')
    pre = next(e for e in hist['eras'] if e['first_sy'] == win['first_sy'] and not e['covid'])
    now = hist['eras'][-1]
    if now['covid'] or now['last_sy'] != win['last_sy']:
        fail('History’s last era no longer runs to the last published year')
    same(round(now['participation'], 4), round(cfig(CO, 'history-lost-staff-seats-and-takers-'
                                                    'together', 'now'), 4), 'history share')
    covid = next(bd for bd in CO['era_series']['bands'] if bd['covid'])
    hy = sorted((y for y in hist['years'] if y['sy'] >= win['first_sy']), key=lambda y: y['sy'])
    E = lambda e: dict(a=SY(e['first_sy']), b=SY(e['last_sy']))
    out['history-courses'] = TP.page(
        'history-courses',
        _fmt('{p1} of Lunenburg High took a history course in {a1} to {b1}, against {p0} in '
             '{a0} to {b0}.', d := dict(p1=SHARE(now['participation']), a1=SY(now['first_sy']),
                                       b1=SY(now['last_sy']), p0=SHARE(pre['participation']),
                                       a0=SY(pre['first_sy']), b0=SY(pre['last_sy']))),
        [fact('p-now', SHARE(now['participation']), 'published',
              'took history, average {a} to {b}', **E(now)),
         fact('p-pre', SHARE(pre['participation']), 'published',
              'took history, average {a} to {b}', **E(pre)),
         fact('fte-now', D2(now['fte'], 'full-time equivalents'), 'published',
              'history teacher FTE, average {a} to {b}', **E(now)),
         fact('fte-pre', D2(pre['fte'], 'full-time equivalents'), 'published',
              'history teacher FTE, average {a} to {b}', **E(pre)),
         fact('seats-now', N(now['seats'], 'student places'), 'published',
              'history places that ran, average {a} to {b}', **E(now)),
         fact('seats-pre', N(pre['seats'], 'student places'), 'published',
              'history places that ran, average {a} to {b}', **E(pre)),
         gap('why-gap', 'why fewer students take history', REQUESTS)],
        [con('The share taking history fell from {a} to {b}, comparing the eras either side of '
             'the pandemic.', ['p-pre', 'p-now'], a=SHARE(pre['participation']),
             b=SHARE(now['participation']),
             notes=[note('The era from {a} to {b} is set aside as the pandemic. That boundary is '
                         'our judgement; the file records nothing about it.', 'hypothesis',
                         a=SY(covid['first_sy']), b=SY(covid['last_sy']))]),
         con('Teacher FTE went from {a} to {b} and places that ran from {c} to {e}.',
             ['fte-pre', 'fte-now', 'seats-pre', 'seats-now'], a=D2(pre['fte']),
             b=D2(now['fte']), c=N(pre['seats']), e=N(now['seats'])),
         con('Fewer posts, a tighter timetable and different choices all fit the same three '
             'numbers.', ['why-gap', 'fte-now', 'p-now'],
             notes=[note('The state files nothing that separates them.', 'gap',
                         closes=REQUESTS)])],
        table=dict(caption='History at Lunenburg High, by school year', views=[dict(
            key='years', label='History', total_col=-1, kinds=['ledger'] * 4,
            columns=['Sections', 'Places', 'Share taking it', 'Teacher FTE'],
            rows=[dict(label='SY%d' % y['sy'], cells=[
                C.num(y['sections']), C.num(y['seats']), C.pct(y['participation'] * 100),
                '%.1f' % y['fte']]) for y in sorted(hy, key=lambda r: -r['sy'])],
            note='DESE’s class-size and teacher files. Places are sections times average class '
                 'size. Single years swing; the page compares averages over eras.')]),
        chart=TP.series('Share of the high school taking history',
                        ['SY%d' % y['sy'] for y in hy], [
            TP.track('Took a history course', [100 * y['participation'] for y in hy])], '%',
            note='Single years swing; the page compares averages either side of the pandemic '
                 'years, a boundary that is ours.'),
        sources=S('class-size', 'teacher-data', 'p-courses'),
        finding_figures=d)

    # ================================================================ computer science
    cs = CO['computer_science']
    hsy = cs['nine_to_twelve_years']
    hs_ran = sum(r['sections'] for r in cs['high'] if r['sy'] in hsy)
    same(hs_ran, cs['hs_sections'], 'high school computer science sections')
    ran = [r for r in cs['high_all'] if r['sy'] in cs['ran_years']]
    if not all(e['first_sy'] <= r['sy'] <= e['last_sy'] for r in ran for e in [g8]):
        fail('the years the high school ran computer science are no longer the grade 8 years')
    lo, hi = min(r['sections'] for r in ran), max(r['sections'] for r in ran)
    msy = [r for r in cs['middle'] if r['sections'] > 0]
    if len(msy) != cs['middle_years'] or len(msy) != len(cs['middle']):
        fail('the middle school no longer runs computer science every year')
    m_last = cs['middle'][-1]
    allr = {r['sy']: r for r in cs['high_all']}
    mrow = {r['sy']: r for r in cs['middle']}
    out['computer-science-courses'] = TP.page(
        'computer-science-courses',
        _fmt('In {n} school years holding grades 9–12, Lunenburg High recorded {s} computer '
             'science section.', d := dict(n=N(len(hsy)), s=N(hs_ran))),
        [fact('hs-sec', N(hs_ran, 'course sections'), 'published',
              'high school sections in {n} years of grades 9–12', allow=('9–12',),
              n=N(len(hsy))),
         fact('hs-one', N(cs['hs_students'], 'students'), 'published',
              'students in that section, {y}', y=SY(cs['hs_year'])),
         fact('ms-years', N(len(msy), 'school years'), 'published',
              'years the middle school ran it, of {n}', n=N(cs['middle_years'])),
         fact('ms-last', N(m_last['sections'], 'course sections'), 'published',
              'middle school sections, {y}', y=SY(m_last['sy'])),
         fact('g8-ran', figure(hi, '%d to %d' % (lo, hi), 'course sections'), 'published',
              'high school sections a year, {a} to {b}', a=SY(g8['first_sy']),
              b=SY(g8['last_sy'])),
         gap('heading-gap', 'computing taught under another subject heading', PROGRAM_OF_STUDIES)],
        [con('In {n} years holding only grades 9–12, the high school ran {s} computer science '
             'section.', ['hs-sec', 'hs-one'], allow=('9–12',), n=N(len(hsy)), s=N(hs_ran)),
         con('The middle school ran it in every one of its {n} years: {s} sections in {y}.',
             ['ms-years', 'ms-last'], n=N(len(msy)), s=N(m_last['sections']), y=SY(m_last['sy'])),
         con('The high school ran {r} sections a year only while grade 8 was in its building.',
             ['g8-ran'], allow=('grade 8',), r=figure(hi, '%d to %d' % (lo, hi))),
         con('This counts one DESE subject heading, so computing taught under another would not '
             'show.', ['heading-gap'],
             notes=[note('A fifth of the high school’s sections are filed as Miscellaneous, with '
                         'no course name.', 'gap', closes=PROGRAM_OF_STUDIES)])],
        table=dict(caption='Computer science sections, by school year', views=[dict(
            key='years', label='Computer and Information Sciences', total_col=-1,
            kinds=['ledger'] * 3, columns=['High school', 'High school students', 'Middle school'],
            rows=[dict(label='SY%d' % y, cells=[
                C.num(allr[y]['sections']), C.num(allr[y]['students']),
                C.num(mrow[y]['sections']) if y in mrow else None])
                  for y in sorted(allr, reverse=True)],
            note='DESE’s class-size file. From SY%d to SY%d grade 8 was taught in the high school '
                 'building. A blank is a year before Lunenburg Middle School existed.'
                 % (g8['first_sy'], g8['last_sy']))]),
        chart=TP.series('Computer science sections', ['SY%d' % y for y in sorted(allr)], [
            TP.track('High school', [allr[y]['sections'] for y in sorted(allr)], 'published', 'bar'),
            TP.track('Middle school', [mrow[y]['sections'] if y in mrow else None
                                       for y in sorted(allr)], 'published', 'bar')],
            'course sections',
            note='DESE’s class-size file. The high school’s early sections fall in the years grade '
                 'eight was taught in its building.'),
        sources=S('class-size', 'enrolment', 'p-courses'),
        finding_figures=d, finding_allow=('9–12',))

    # ================================================================ AP participation
    Y = {r['sy']: r for r in AP['years']}
    APY = sorted(AP['years'], key=lambda r: r['sy'])
    SYL = lambda r: 'SY%d' % r['sy']
    y1, y0 = AP['last_sy'], AP['first_sy']
    r1, r0 = Y[y1], Y[y0]
    peak = max(AP['years'], key=lambda r: r['takers'])
    speak = max(AP['years'], key=lambda r: r['share_1112'])
    same(peak['takers'], cfig(AP, 'two-in-five-upperclassmen-sit-an-ap-exam', 'peak'), 'AP peak')
    same(r1['takers'], cfig(AP, 'two-in-five-upperclassmen-sit-an-ap-exam', 'takers'), 'AP takers')
    offered_gap = gap('offered-gap', 'which AP courses the high school offered each year',
                      PROGRAM_OF_STUDIES)
    out['ap-participation'] = TP.page(
        'ap-participation',
        _fmt('{t} students sat at least one AP exam in {y}, {s} sittings between them; the count '
             'peaked at {p} in {yp}.', d := dict(t=N(r1['takers']), y=SY(y1), s=N(r1['sittings']),
                                                p=N(peak['takers']), yp=SY(peak['sy']))),
        [fact('takers', N(r1['takers'], 'students'), 'published',
              'students who sat at least one exam, {y}', y=SY(y1)),
         fact('sittings', N(r1['sittings'], 'exams'), 'published', 'exams sat, {y}', y=SY(y1)),
         fact('g1112', N(r1['g1112'], 'students'), 'published',
              'students in grades 11 and 12, {y}', allow=('11', '12'), y=SY(y1)),
         fact('share', SHARE(r1['share_1112'], 0), 'estimate',
              'takers over grades 11 and 12, {y}', allow=('11', '12'), y=SY(y1)),
         fact('share-peak', SHARE(speak['share_1112'], 0), 'estimate',
              'the same ratio at its highest, {y}', y=SY(speak['sy'])),
         fact('takers-first', N(r0['takers'], 'students'), 'published',
              'students who sat an exam, {y}', y=SY(y0)),
         fact('peak', N(peak['takers'], 'students'), 'published',
              'students who sat an exam, {y}, the most', y=SY(peak['sy'])),
         offered_gap],
        [con('{t} students sat {s} exams in {y}, against {t0} students in {y0} and {p} in {yp}.',
             ['takers', 'sittings', 'takers-first', 'peak'], t=N(r1['takers']),
             s=N(r1['sittings']), y=SY(y1), t0=N(r0['takers']), y0=SY(y0), p=N(peak['takers']),
             yp=SY(peak['sy'])),
         con('That is about {a} of grades 11 and 12, against {b} in {yb}.',
             ['share', 'g1112', 'share-peak'], allow=('11', '12'),
             a=SHARE(r1['share_1112'], 0), b=SHARE(speak['share_1112'], 0), yb=SY(speak['sy']),
             notes=[note('The ratio is ours and approximate: a tenth grader can sit an exam, and '
                         'the two DESE files count on different days.', 'hypothesis')]),
         con('A count of exams sat cannot tell a course not offered from one not chosen.',
             ['offered-gap', 'takers'],
             notes=[note('DESE counts exams sat, not courses taught.', 'gap',
                         closes=PROGRAM_OF_STUDIES)])],
        table=dict(caption='AP exams at Lunenburg High, by school year', views=[dict(
            key='years', label='Participation', total_col=-1, kinds=['ledger'] * 3 + ['stated'],
            columns=['Students', 'Exams', 'Grades 11–12', 'Ratio'],
            rows=[dict(label='SY%d' % r['sy'], cells=[
                C.num(r['takers']), C.num(r['sittings']), C.num(r['g1112']),
                C.pct(r['share_1112'] * 100, 0)]) for r in sorted(AP['years'], key=lambda r: -r['sy'])],
            note='DESE’s AP participation file and its enrolment by grade. The ratio is our '
                 'division of one by the other, an approximation.')]),
        chart=TP.series('Students who sat an AP exam', [SYL(r) for r in APY], [
            TP.track('Sat at least one exam', [r['takers'] for r in APY], 'published', 'bar')],
            'students', note='DESE’s AP participation file. A student is counted once however many '
                             'exams they sat.'),
        said=[said(CO, 'options')],
        sources=S('ap-part', 'enrolment', 'p-ap'),
        finding_figures=d)

    # ================================================================ AP scores
    best = max(AP['years'], key=lambda r: r['pass_share'])
    worst = min(AP['years'], key=lambda r: r['pass_share'])
    two_ago = Y[y1 - 2]
    if best['sy'] != y1:
        fail('SY%d is no longer the best pass rate in the file; the AP scores page needs '
             'rewriting' % y1)
    if sum(r1['scores']) != r1['sittings']:
        fail('the score counts no longer sum to the sittings')
    same(r1['pass_share'], cfig(AP, 'the-pass-rate-is-the-highest-in-the-file', 'best'), 'AP pass')
    out['ap-scores'] = TP.page(
        'ap-scores',
        _fmt('{p} of AP tests scored 3 or better in {y}, the highest of {n} years; the lowest '
             'was {w} in {yw}.', d := dict(p=SHARE(r1['pass_share']), y=SY(y1),
                                           n=N(len(AP['years'])), w=SHARE(worst['pass_share']),
                                           yw=SY(worst['sy']))),
        [fact('pass', SHARE(r1['pass_share']), 'published', 'of tests scored 3 to 5, {y}',
              allow=('3', '5'), y=SY(y1)),
         fact('two-ago', SHARE(two_ago['pass_share']), 'published', 'of tests scored 3 to 5, {y}',
              allow=('3', '5'), y=SY(two_ago['sy'])),
         fact('worst', SHARE(worst['pass_share']), 'published',
              'of tests scored 3 to 5, {y}, the lowest', allow=('3', '5'), y=SY(worst['sy'])),
         fact('tests', N(r1['sittings'], 'tests'), 'published', 'tests scored, {y}', y=SY(y1)),
         fact('fives', N(r1['scores'][4], 'tests'), 'published', 'tests scoring 5, {y}',
              allow=('5',), y=SY(y1)),
         fact('ones', N(r1['scores'][0], 'tests'), 'published', 'tests scoring 1, {y}',
              allow=('1',), y=SY(y1))],
        [con('{p} of tests scored 3 or better in {y}, the highest of {n} published years.',
             ['pass', 'tests'], allow=('3',), p=SHARE(r1['pass_share']), y=SY(y1),
             n=N(len(AP['years'])),
             notes=[note('Better teaching, different students choosing to sit, or a shift toward '
                         'subjects that score higher all fit. The file separates none of them.',
                         'hypothesis')]),
         con('The lowest was {w} in {yw}; two years before {y} it was {t}.', ['worst', 'two-ago'],
             w=SHARE(worst['pass_share']), yw=SY(worst['sy']), y=SY(y1),
             t=SHARE(two_ago['pass_share'])),
         con('It is a share of tests, not students: one who sits three exams counts three times.',
             ['tests', 'fives', 'ones'])],
        table=dict(caption='AP test scores at Lunenburg High, by school year', views=[dict(
            key='years', label='Scores', total_col=-1, kinds=['ledger'] * 4,
            columns=['Tests', 'Scored 5', 'Scored 1', '3 or better'],
            rows=[dict(label='SY%d' % r['sy'], cells=[
                C.num(sum(r['scores'])), C.num(r['scores'][4]), C.num(r['scores'][0]),
                C.pct(r['pass_share'] * 100)]) for r in sorted(AP['years'], key=lambda r: -r['sy'])],
            note='DESE’s AP performance file, all subjects. A score of 3 is the usual threshold '
                 'for college credit.')]),
        chart=TP.series('AP tests scoring three or better', [SYL(r) for r in APY], [
            TP.track('Share of tests', [100 * r['pass_share'] for r in APY])], '%',
            note='DESE’s AP performance file, all subjects: a share of tests, not of students.'),
        sources=S('ap-perf', 'p-ap'),
        finding_figures=d, finding_allow=('3',))

    # ================================================================ AP subjects
    fam = {f['family']: f for f in AP['families']}
    ys = AP['compare_sy']
    hum = fam['History and Social Science']['now'] + fam['English Language Arts']['now']
    stem_now = fam['Math and Computer Science']['now'] + fam['Science and Technology']['now']
    stem_then = fam['Math and Computer Science']['then'] + fam['Science and Technology']['then']
    lang = fam['Foreign Languages']
    if sum(f['now'] for f in AP['families']) != r1['sittings']:
        fail('the subject families no longer sum to the sittings')
    if sum(f['then'] for f in AP['families']) != Y[ys]['sittings']:
        fail('the subject families no longer sum to the SY%d sittings' % ys)
    same(hum, cfig(AP, 'the-exams-are-english-and-history', 'humanities'), 'AP humanities')
    suppressed = [f['family'] for f in AP['families'] if 'suppressed' in f['basis_now']]
    # Axis labels only; the table beside the chart carries DESE's own family names.
    FAM_SHORT = {'History and Social Science': 'History', 'English Language Arts': 'English',
                 'Math and Computer Science': 'Math and CS', 'Science and Technology': 'Science',
                 'Arts': 'Arts', 'Foreign Languages': 'Languages'}
    if set(FAM_SHORT) != set(fam):
        fail('the AP subject families changed; name the new one for the chart')
    out['ap-subjects'] = TP.page(
        'ap-subjects',
        _fmt('{h} of {s} AP exams in {y} were English or history; science and math were {m}.',
             d := dict(h=N(hum), s=N(r1['sittings']), y=SY(y1), m=N(stem_now))),
        [fact('hum', N(hum, 'exams'), 'published', 'English and history exams, {y}', y=SY(y1)),
         fact('hum-share', SHARE(hum / r1['sittings'], 0), 'published',
              'of all exams, {y}', y=SY(y1)),
         fact('stem-now', N(stem_now, 'exams'), 'published', 'science and math exams, {y}',
              y=SY(y1)),
         fact('stem-then', N(stem_then, 'exams'), 'published', 'science and math exams, {y}',
              y=SY(ys)),
         fact('lang-now', N(lang['now'], 'exams'), 'published', 'language exams, {y}', y=SY(y1)),
         fact('lang-then', N(lang['then'], 'exams'), 'published', 'language exams, {y}',
              y=SY(ys)),
         offered_gap],
        [con('{h} of {s} exams in {y} were English or history, {p} of the total.',
             ['hum', 'hum-share'], h=N(hum), s=N(r1['sittings']), y=SY(y1),
             p=SHARE(hum / r1['sittings'], 0)),
         con('Science and math exams went from {a} in {y0} to {b}; language exams from {c} to {e}.',
             ['stem-then', 'stem-now', 'lang-then', 'lang-now'], a=N(stem_then), y0=SY(ys),
             b=N(stem_now), c=N(lang['then']), e=N(lang['now'])),
         con('An exam count cannot tell a closed door from an empty room.', ['offered-gap'],
             notes=[note('Where DESE suppresses a small subject in one file it is read from the '
                         'other; the table says which.', 'gap', closes=PROGRAM_OF_STUDIES)])],
        table=dict(caption='AP exams by subject family', views=[dict(
            key='families', label='Exams sat', total_col=-1, kinds=['ledger'] * 3,
            columns=['SY%d' % ys, 'SY%d' % y1, '3 or better, SY%d' % y1],
            rows=[dict(label=f['family'] + (' (performance file)' if 'suppressed' in
                                            f['basis_now'] else ''),
                       cells=[C.num(f['then']), C.num(f['now']),
                              C.pct(f['pass_share'] * 100) if f['pass_share'] is not None
                              else None]) for f in AP['families']],
            note='DESE’s AP participation file; where it suppresses a family, the performance '
                 'file’s test count. A blank share is one DESE suppresses.')]),
        chart=TP.series('AP exams by subject family', [FAM_SHORT[f['family']] for f in AP['families']], [
            TP.track('SY%d' % ys, [f['then'] for f in AP['families']], 'published', 'bar'),
            TP.track('SY%d' % y1, [f['now'] for f in AP['families']], 'published', 'bar')], 'exams',
            note='Exams sat, from DESE’s participation file; where it suppresses a family, the '
                 'performance file’s count.'),
        said=[said(CO, 'apstats')],
        sources=S('ap-part', 'ap-perf', 'p-ap'),
        finding_figures=d)

    # ================================================================ announced cuts
    tot, f20 = CR['totals'], CR['fy2020']
    if len(f20['withdrawn']) != f20['named_march'] - f20['named_april']:
        fail('the FY2020 withdrawals no longer reconcile to the two lists')
    same(len(f20['withdrawn']), cfig(CR, 'a-cut-list-is-a-draft', 'withdrawn'), 'FY2020 withdrawn')
    if sum(p['reductions'] for p in CR['per_year']) != tot['reductions']:
        fail('the cut register’s years no longer sum to its total')
    lhs, lms = f20['lhs_foreign'], f20['lms_foreign']
    CRY = sorted(CR['per_year'], key=lambda p: p['fy'])
    outcome_gap = gap('outcome-gap', 'whether any named post was removed', POSITIONS)
    dm, dl = '6 March 2019', '3 April 2019'
    out['announced-cuts'] = TP.page(
        'announced-cuts',
        _fmt('The district named {r} reductions in {d} budget documents across {c} cycles; none '
             'records what became of a post.', d := dict(r=N(tot['reductions']),
                                                         d=N(tot['documents']),
                                                         c=N(tot['cycles']))),
        [fact('reductions', N(tot['reductions'], 'reductions named'), 'published',
              'reductions named, {a} to {b}', a=FY(CR['span']['first_fy']),
              b=FY(CR['span']['last_fy'])),
         fact('restorations', N(tot['restorations'], 'items named'), 'published',
              'restorations and additions named'),
         fact('documents', N(tot['documents'], 'documents'), 'published',
              'district budget documents, {c} cycles', c=N(tot['cycles'])),
         fact('named', N(f20['named_march'], 'positions'), 'published',
              'posts on the list of {d}', d=dm),
         fact('withdrawn', N(len(f20['withdrawn']), 'positions'), 'published',
              'of them off the list presented {d}', d=dl),
         fact('lhs', D1(lhs['after'], 'full-time equivalents'), 'published',
              'high school language FTE, {y}; {b} a year before', y=FY(lhs['after_fy']),
              b=D1(lhs['before'])),
         fact('lms', D1(lms['after'], 'full-time equivalents'), 'published',
              'middle school language FTE, {y}; {b} a year before', y=FY(lms['after_fy']),
              b=D1(lms['before'])),
         outcome_gap],
        [con('The district named {r} reductions and {s} restorations or additions in {d} '
             'documents.', ['reductions', 'restorations', 'documents'], r=N(tot['reductions']),
             s=N(tot['restorations']), d=N(tot['documents'])),
         con('Of {n} posts on the list of {dm}, {w} were off it four weeks later.',
             ['named', 'withdrawn'], dm=dm, n=N(f20['named_march']),
             w=N(len(f20['withdrawn']))),
         con('One restored post was a high school language teacher; that FTE went {a} to {b}, '
             'the middle’s {c} to {e}.', ['lhs', 'lms'], a=D1(lhs['before']), b=D1(lhs['after']),
             c=D1(lms['before']), e=D1(lms['after']),
             notes=[note('DESE apportions teaching time by subject, which moves when a timetable '
                         'moves. Agreement is consistency, not proof.', 'hypothesis')]),
         con('A cut list is a statement of intent; what became of each post is not published.',
             ['outcome-gap', 'reductions'],
             notes=[note('A grant can pay for a post, a retirement can absorb a cut, and a later '
                         'vote can restore one.', 'gap', closes=POSITIONS)])],
        table=dict(caption='Reductions named in district budget documents, by cycle', views=[dict(
            key='cycles', label='By budget year', total_col=-1, kinds=['stated'] * 4,
            columns=['Documents', 'Reductions', 'Restorations', 'On the adopted list'],
            rows=[dict(label=C.fy(p['fy']), cells=[
                C.num(p['documents']), C.num(p['reductions']), C.num(p['restorations']),
                C.num(p['operative'])]) for p in sorted(CR['per_year'], key=lambda p: -p['fy'])],
            note='Counts of rows the district printed, quoted at their pages in the register. A '
                 'row is a claim the district published, not an event.')]),
        chart=TP.series('What the district’s budget documents named', [C.fy(p['fy']) for p in CRY], [
            TP.track('Reductions', [p['reductions'] for p in CRY], 'stated', 'bar'),
            TP.track('Restorations and additions', [p['restorations'] for p in CRY], 'stated',
                     'bar')], 'items named',
            note='Rows the district printed, by budget year. A row is a claim it published, not an '
                 'event.'),
        said=[said(CR, 'layoffs'), said(CR, 'staffing-dispute')],
        sources=doc_sources([(x['path'], x['title']) for x in CR['documents']]) + S('p-cuts'),
        finding_figures=d)

    # ================================================================ override cut lists
    f25 = CR['fy2025']
    bal = f25['ballot']
    without = f25['with_override'] + f25['saved']
    same(without, cfig(CR, 'the-override-changed-which-cuts-happened', 'without'), 'without list')
    if len(f25['pairs']) != f25['paired'] or f25['paired'] != f25['with_override']:
        fail('the nine posts on the override list no longer all pair to the ESSER list')
    vote_day = 'May 2024'
    pair_gap = gap('post-gap', 'what became of any post on either list', POSITIONS)
    out['override-cut-lists'] = TP.page(
        'override-cut-lists',
        _fmt('The %s override took {s} posts off the cut list; the {w} left match posts listed '
             'as cut for loss of ESSER.' % vote_day, d := dict(s=N(f25['saved']),
                                                         w=N(f25['with_override']))),
        [fact('without', N(without, 'positions'), 'published', 'posts to be cut without an override'),
         fact('with', N(f25['with_override'], 'positions'), 'published',
              'posts to be cut with one'),
         fact('yes', N(bal['yes'], 'votes'), 'published', 'votes for the override, {d}', d=vote_day),
         fact('no', N(bal['no'], 'votes'), 'published', 'votes against'),
         fact('saved', N(f25['saved'], 'positions'), 'published', 'posts off the operative list'),
         fact('paired', N(f25['paired'], 'positions'), 'estimate',
              'of the {w} that stayed pair to a post cut for loss of ESSER',
              w=N(f25['with_override'])),
         pair_gap],
        [con('Before the {d} vote the committee published two lists: {a} posts without an '
             'override, {b} with.', ['without', 'with'], d=vote_day, a=N(without),
             b=N(f25['with_override'])),
         con('The override passed {y} to {n}, so {s} posts came off the list that applied.',
             ['yes', 'no', 'saved'], y=N(bal['yes']), n=N(bal['no']), s=N(f25['saved'])),
         con('Each of the {n} that stayed matches a post the budget update lists as cut for loss '
             'of ESSER.', ['paired', 'with'], n=N(f25['paired']),
             notes=[note('The pairing of the two documents’ job titles is our reading; both '
                         'wordings are in the table.', 'hypothesis')]),
         con('Two lists and a ballot show which list applied, not what happened to any post.',
             ['post-gap'],
             notes=[note('Nothing published records which posts were filled after the vote.',
                         'gap', closes=POSITIONS)])],
        table=dict(caption='The posts still cut with the override, as each document prints them',
                   views=[dict(
            key='pairs', label='Paired wordings', total_col=-1, kinds=['stated'],
            columns=['As the budget update lists it, cut for loss of ESSER'],
            rows=[dict(label=p['with_override'], cells=[p['esser']]) for p in f25['pairs']],
            note='Left: the School Committee’s override statement. Right: the FY25 '
                 'Superintendent’s Budget Update. The pairing is ours.')]),
        chart=TP.parts('Posts on the list without an override', [
            ('Still cut with the override', f25['with_override']),
            ('Off the list once it passed', f25['saved'])], 'positions', basis='stated',
            note='The School Committee’s two published lists, %s. Which posts went is not '
                 'published.' % vote_day, note_allow=(vote_day,)),
        said=[said(GU, 'burden'), said(GU, 'beyond')],
        sources=doc_sources([(x['path'], x['title']) for x in CR['documents']
                             if x['fy'] == 2025]) + S('p-cuts'),
        finding_figures=d, finding_allow=(vote_day,))

    # ================================================================ cuts against state counts
    if tot['moved_with'] + tot['moved_other'] + tot['unresolved'] + tot['blind'] != tot['measurable']:
        fail('the cut register’s verdicts no longer sum to the adopted cuts it can test')
    tested = tot['measurable'] - tot['blind']
    same(tested, cfig(CR, 'half-of-what-can-be-checked-checks-out', 'tested'), 'tested cuts')
    hc_fy = CR['span']['first_fy']
    out['cuts-against-state-counts'] = TP.page(
        'cuts-against-state-counts',
        _fmt('Of {m} adopted school cuts, {b} name a job no series counts; of the other {t}, '
             'the state’s count fell with {w}.', d := dict(b=N(tot['blind']), m=N(tot['measurable']),
                                                   t=N(tested), w=N(tot['moved_with']))),
        [fact('measurable', N(tot['measurable'], 'adopted cuts'), 'published',
              'adopted cuts old enough to test'),
         fact('blind', N(tot['blind'], 'adopted cuts'), 'published',
              'name a job no series counts by school'),
         fact('blind-share', PCT(tot['blind_share']), 'published', 'of adopted cuts untestable'),
         fact('tested', N(tested, 'adopted cuts'), 'published', 'that the state’s teacher count reaches'),
         fact('with', N(tot['moved_with'], 'adopted cuts'), 'published',
              'where the count fell with the cut'),
         fact('other', N(tot['moved_other'], 'adopted cuts'), 'published',
              'where it moved the other way'),
         fact('unresolved', N(tot['unresolved'], 'adopted cuts'), 'published',
              'where it moved by less than stated'),
         fact('not-yet', N(tot['not_yet'], 'adopted cuts'), 'published',
              'too recent to test'),
         gap('staff-gap', 'whether a non-teaching post named on a list went', POSITIONS)],
        [con('{b} of {m} adopted cuts name a job no published series counts by school.',
             ['blind', 'measurable', 'blind-share'], b=N(tot['blind']), m=N(tot['measurable'])),
         con('Of the {t} the state’s teacher count reaches, it fell with {w}, rose against {o} and '
             'moved too little in {u}.', ['tested', 'with', 'other', 'unresolved'], t=N(tested),
             w=N(tot['moved_with']), o=N(tot['moved_other']), u=N(tot['unresolved'])),
         con('A matching move is consistency, not proof: the state counts one October day a year.',
             ['with', 'staff-gap'],
             notes=[note('A post cut in June and filled again in November is invisible to it.',
                         'gap', closes=POSITIONS)])],
        table=dict(caption='Adopted cuts tested against DESE teacher counts, by budget year',
                   views=[dict(
            key='years', label='By budget year', total_col=-1, kinds=['stated'] + ['ledger'] * 4,
            columns=['Adopted', 'No series', 'Fell with it', 'Other way', 'Too little'],
            rows=[dict(label=C.fy(p['fy']), cells=[
                C.num(p['operative']), C.num(p['blind']), C.num(p['moved_with']),
                C.num(p['moved_other']), C.num(p['unresolved'])])
                  for p in sorted(CR['per_year'], key=lambda p: -p['fy'])],
            note='Adopted counts are the district’s own lists; the tests are against DESE teacher '
                 'FTE. The tolerance and the mapping of titles to subjects are ours.')]),
        chart=TP.parts('Adopted cuts old enough to test', [(l, v) for l, v in (
            ('No series counts the job', tot['blind']),
            ('State count fell with the cut', tot['moved_with']),
            ('Moved by less than stated', tot['unresolved']),
            ('Moved the other way', tot['moved_other'])) if v], 'adopted cuts', basis='stated',
            note='The district’s adopted lists, tested against DESE teacher counts; the tolerance '
                 'and the title mapping are ours.'),
        sources=S('teacher-data', 'p-cuts'),
        finding_figures=d)

    # ================================================================ lines cut to zero
    T = SF['totals']
    ev = [e for e in SF['events']]
    if len(ev) != T['events'] or sum(1 for e in ev if e['returned']) != T['returned']:
        fail('the stopped-funding events no longer reconcile to its totals')
    py = [p for p in SF['per_year'] if p['n']]
    pya = sorted(py, key=lambda p: p['fy'])
    if any(p['returned_n'] + p['stayed_n'] != p['n'] for p in py):
        fail('a year’s lines cut to zero no longer split into came back and never again')
    ef, el = min(p['fy'] for p in py), max(p['fy'] for p in py)
    book_fy = SF['span']['last_fy']
    book = next(c['total'] for c in SF['coverage'] if c['fy'] == book_fy)
    same(book, cfig(SF, 'what-stops-for-good-is-small-and-mostly-staff-money', 'book'), 'book')
    staff = [p for p in SF['permanent'] if p['buys'] == 'Teaching and specialist staff']
    staff_dollars = sum(p['last_funded'] for p in staff)
    same(staff_dollars, cfig(SF, 'what-stops-for-good-is-small-and-mostly-staff-money',
                             'staff_dollars'), 'staff dollars')
    if sum(p['last_funded'] for p in SF['permanent']) != T['permanent_dollars']:
        fail('the permanent lines no longer sum to their total')
    out['lines-cut-to-zero'] = TP.page(
        'lines-cut-to-zero',
        _fmt('{r} of {e} school lines cut to zero were funded again later; the {p} that never '
             'were carried {d}.', d := dict(r=N(T['returned']), e=N(T['events']),
                                                           p=N(T['permanent']),
                                                           d=USD(T['permanent_dollars']))),
        [fact('events', N(T['events'], 'budget lines'), 'published',
              'lines cut to a printed zero, {a} to {b}', a=FY(ef), b=FY(el)),
         fact('returned', N(T['returned'], 'budget lines'), 'published', 'funded again later'),
         fact('was', USD(T['event_dollars']), 'published', 'those lines carried the year before'),
         fact('back', USD(T['returned_dollars']), 'published', 'of it came back on the same line'),
         fact('permanent', N(T['permanent'], 'budget lines'), 'published',
              'never funded again'),
         fact('perm-dollars', USD(T['permanent_dollars']), 'published',
              'those carried when last funded'),
         fact('book', USD(book), 'published', 'school budget book total, {y}', y=FY(book_fy)),
         fact('staff', USD(staff_dollars), 'estimate',
              'of it on {n} staff lines, by our grouping', n=N(len(staff))),
         fact('vanished', N(T['vanished'], 'budget lines'), 'published',
              'lines that left the book altogether'),
         gap('book-gap', 'whether a line that left the book stopped being funded',
             'a crosswalk from the FY2022 budget-book line list to FY2023’s, or the MUNIS '
             'year-end expense report for the school department')],
        [con('{r} of {e} lines cut to zero from {a} to {b} were funded again in a later year.',
             ['events', 'returned', 'was', 'back'], r=N(T['returned']), e=N(T['events']),
             a=FY(ef), b=FY(el)),
         con('The {p} never funded again carried {d} when last funded, {s} of the {y} book total.',
             ['permanent', 'perm-dollars', 'book', 'staff'], p=N(T['permanent']),
             d=USD(T['permanent_dollars']), s=PCT(100 * T['permanent_dollars'] / book),
             y=FY(book_fy),
             notes=[note('A line at zero is not a post removed: the money can have moved to '
                         'another line, a grant, or a differently spelled line.', 'hypothesis')]),
         con('{v} lines left the book altogether; for any one of them, absence is a fact about '
             'the document.', ['vanished', 'book-gap'], v=N(T['vanished']),
             notes=[note('Between {a} and {b} the book dropped about a third of its lines while '
                         'its total rose.', 'gap', a=FY(SF['shape']['fy']),
                         b=FY(SF['shape']['next_fy']),
                         closes='a crosswalk between the two books’ line lists')])],
        table=dict(caption='School budget lines cut to a printed zero, by year', views=[dict(
            key='years', label='By year the line went to zero', total_col=-1,
            kinds=['ledger'] * 4, columns=['Cut to zero', 'Came back', 'Never again',
                                           'Carried the year before'],
            rows=[dict(label=C.fy(p['fy']), cells=[
                C.num(p['n']), C.num(p['returned_n']), C.num(p['stayed_n']), C.usd(p['dollars'])])
                  for p in sorted(py, key=lambda p: -p['fy'])],
            note='The district’s own budget books, restating each closed year. A line is net of '
                 'grants and fees, and a budget line is not a programme.')]),
        chart=TP.series('School lines cut to a printed zero', [C.fy(p['fy']) for p in pya], [
            TP.track('Funded again later', [p['returned_n'] for p in pya], 'published', 'bar'),
            TP.track('Never funded again', [p['stayed_n'] for p in pya], 'published', 'bar')],
            'budget lines', stacked=True,
            note='By the year the line went to zero, in the district’s own budget books. A line '
                 'at zero is not a programme ended.'),
        said=[said(SF, 'psychologist')],
        sources=doc_sources([(next(k for k in man if k.startswith('district-budget/docs/') and
                                   os.path.splitext(os.path.basename(k))[0] ==
                                   os.path.basename(t)[:-4]),
                              os.path.basename(t)[:-4]) for t in SF['documents']]) + S('p-stopped'),
        finding_figures=d)

    # ================================================================ grant endings
    ly = GU['latest_year']
    by = {r['fy']: r for r in GU['by_year']}
    GUY = sorted(GU['by_year'], key=lambda r: r['fy'])
    cur = by[ly]
    sw, rd = cur['swap'], cur['reduction']
    fall = -(sw['d_grants'] + rd['d_grants'])
    same(fall, cfig(GU, 'half-of-it-was-replaced-and-half-just-stopped', 'grant_fall'), 'grant fall')
    rep_share = 100 * -sw['d_grants'] / fall
    ins = cfig(GU, 'the-biggest-rise-was-a-reporting-gap', 'before')
    ins_prev = cfig(GU, 'the-biggest-rise-was-a-reporting-gap', 'before2')
    ins_now = cfig(GU, 'the-biggest-rise-was-a-reporting-gap', 'now')
    out['grant-endings'] = TP.page(
        'grant-endings',
        _fmt('{s} of the grant money that ran out in {y} was replaced from the general fund; the '
             'rest was not.', d := dict(s=PCT(rep_share), y=FY(ly))),
        [fact('fall', USD(fall), 'published', 'gross grant fall, in the areas where it fell, {y}', y=FY(ly)),
         fact('functions', N(sw['n'] + rd['n'], 'areas of spending'), 'published',
              'areas of school spending where it fell'),
         fact('replaced', USD(-sw['d_grants']), 'published',
              'fell in the {n} where the general fund rose', n=N(sw['n'])),
         fact('town-rose', USD(sw['d_gen_fund']),
              'published', 'the general fund’s rise in those {n}', n=N(sw['n'])),
         fact('not-replaced', USD(-rd['d_grants']), 'published',
              'fell in the {n} where it did not', n=N(rd['n'])),
         fact('town-fell', USD(-rd['d_gen_fund']), 'published',
              'the general fund’s further fall in those {n}', n=N(rd['n'])),
         fact('share', PCT(rep_share), 'estimate', 'of the fall replaced, by our classification'),
         gap('which-gap', 'which grant ended, and which posts it paid for', GRANTS)],
        [con('{f} of grant spending fell in {y}, across {n} areas of school spending.',
             ['fall', 'functions'], f=USD(fall), y=FY(ly), n=N(sw['n'] + rd['n'])),
         con('In {a} of them the general fund rose {b}; in the other {c} it fell a further {e}.',
             ['town-rose', 'town-fell', 'replaced', 'not-replaced'], a=N(sw['n']),
             b=USD(sw['d_gen_fund']), c=N(rd['n']), e=USD(-rd['d_gen_fund'])),
         con('By our classification {s} of the fall was replaced and {r} was not.',
             ['share', 'replaced', 'not-replaced'], s=PCT(rep_share), r=USD(-rd['d_grants']),
             notes=[note('A rise beside a fall in one area fits the town picking up a cost and two '
                         'unrelated changes alike. The general fund also carries Chapter 70 aid.',
                         'hypothesis', allow=('Chapter 70',)),
                     note('Employee insurance reads {a} for {y}, against {b} and {c} either side, '
                          'so most of its {z} rise is that gap closing.', 'gap', a=USD(ins), y=FY(ly - 1),
                          b=USD(ins_prev), c=USD(ins_now), z=FY(ly),
                          closes='a statement of where the district reported FY2024 active '
                                 'employee insurance')]),
         con('DESE reports a fund total; it names no grant and no post.', ['which-gap'],
             notes=[note('Nothing published maps a grant to the posts it paid for.', 'gap',
                         closes=GRANTS)])],
        table=dict(caption='Grant spending that fell, by year and what the town did',
                   views=[dict(
            key='years', label='By fiscal year', total_col=-1, kinds=['ledger'] * 4,
            columns=['Grants fell, town rose', 'Town rose by', 'Grants fell, town fell',
                     'Town fell by'],
            rows=[dict(label=C.fy(r['fy']), cells=[
                C.usd(-r['swap']['d_grants']), C.usd(r['swap']['d_gen_fund']),
                C.usd(-r['reduction']['d_grants']), C.usd(-r['reduction']['d_gen_fund'])])
                  for r in sorted(GU['by_year'], key=lambda r: -r['fy'])],
            note='DESE’s End of Year Financial Report, each function compared with the year '
                 'before. Sorting functions by the two signs is ours.')]),
        chart=TP.series('Grant spending that fell, and the town',
                        [C.fy(r['fy']) for r in GUY], [
            TP.track('General fund rose in the same area', [-r['swap']['d_grants'] for r in GUY],
                     'published', 'bar'),
            TP.track('General fund did not', [-r['reduction']['d_grants'] for r in GUY],
                     'published', 'bar')], '$', stacked=True,
            note='DESE’s End of Year Financial Report, each area of spending against the year '
                 'before. The sorting by sign is ours.'),
        said=[said(GU, 'loss'), said(GU, 'paras')],
        sources=S('eoyr', 'p-grants'),
        finding_figures=d)

    # ================================================================ outside money share
    ser = {r['fy']: r for r in GU['series']}
    f0, f1 = GU['fy_first'], GU['fy_last']
    same(ser[f0]['town_share'], GU['town_share_first'], 'first town share')
    same(ser[f1]['town_share'], GU['town_share_last'], 'last town share')
    cf = GU['counterfactual']
    if cf['is_measurement']:
        fail('the counterfactual is now marked a measurement; this page calls it ours')
    # The year's change is read off the DISTRICT TOTALS -- the series the share itself comes
    # from. The payload's own conclusion states a different pair, summed over the functions
    # present in both years; the two disagree (see the report), and this page uses the series.
    gf_rise = ser[f1]['gen_fund'] - ser[f1 - 1]['gen_fund']
    tot_chg = ser[f1]['total'] - ser[f1 - 1]['total']
    gr_chg = ser[f1]['grants'] - ser[f1 - 1]['grants']
    if gf_rise <= 0 or tot_chg <= 0 or gr_chg >= 0:
        fail('the FY%d direction of the three district totals changed; rewrite the sentence' % f1)
    lo_sh = min(GU['series'], key=lambda r: r['town_share'])
    hi_sh = max(GU['series'], key=lambda r: r['town_share'])
    out['outside-money-share'] = TP.page(
        'outside-money-share',
        _fmt('The general fund paid {a} of school spending in {y0} and {b} in {y1}; grants and '
             'other funds the rest.', d := dict(a=PCT(ser[f0]['town_share']), y0=FY(f0),
                                         b=PCT(ser[f1]['town_share']), y1=FY(f1))),
        [fact('share-first', PCT(ser[f0]['town_share']), 'published',
              'general fund share of spending, {y}', y=FY(f0)),
         fact('share-last', PCT(ser[f1]['town_share']), 'published',
              'general fund share of spending, {y}', y=FY(f1)),
         fact('share-hi', PCT(hi_sh['town_share']), 'published', 'the highest share, {y}',
              y=FY(hi_sh['fy'])),
         fact('points', figure(GU['town_share_points'], C.points(GU['town_share_points'])),
              'published', 'change in the share, {a} to {b}', a=FY(f0), b=FY(f1)),
         fact('counterfactual', USD(cf['difference']), 'estimate',
              'a year, at {y} spending, if the {y0} split held', y=FY(f1), y0=FY(f0)),
         fact('gf-rise', USD(gf_rise), 'published', 'general fund rise, {y}', y=FY(f1)),
         fact('gr-fall', USD(-gr_chg), 'published', 'grant and revolving fall, {y}', y=FY(f1)),
         fact('tot-rise', USD(tot_chg), 'published', 'rise across all funds, {y}', y=FY(f1))],
        [con('The general fund paid {a} in {y0} and {b} in {y1}, after a high of {h} in {yh}.',
             ['share-first', 'share-last', 'points', 'share-hi'], a=PCT(ser[f0]['town_share']),
             y0=FY(f0), b=PCT(ser[f1]['town_share']), y1=FY(f1), h=PCT(hi_sh['town_share']),
             yh=FY(hi_sh['fy']),
             notes=[note('Grant programmes starting and ending, state payments and town '
                         'appropriations all move it, and nothing here separates them.',
                         'hypothesis'),
                    note('The general fund holds Chapter 70 state aid as well as local taxes, so '
                         'its share is not the share local taxpayers paid.', 'gap',
                         allow=('Chapter 70',),
                         closes='DESE’s net school spending report, which separates Chapter 70 '
                                'from the required local contribution')]),
         con('At {y} spending, {p} is {d} a year: our arithmetic, not a forecast.',
             ['points', 'counterfactual'], y=FY(f1),
             p=figure(GU['town_share_points'], C.points(GU['town_share_points'])),
             d=USD(cf['difference'])),
         con('In {y} the general fund rose {a} and grants fell {b}; all funds rose {c}.',
             ['gf-rise', 'gr-fall', 'tot-rise'], y=FY(f1), a=USD(gf_rise), b=USD(-gr_chg),
             c=USD(tot_chg))],
        table=dict(caption='Lunenburg school spending by fund, by year', views=[dict(
            key='years', label='By fiscal year', total_col=2, kinds=['ledger'] * 4,
            columns=['General fund', 'Grants and revolving', 'All funds', 'General fund share'],
            rows=[dict(label=C.fy(y), cells=[
                C.usd(ser[y]['gen_fund']), C.usd(ser[y]['grants']), C.usd(ser[y]['total']),
                C.pct(ser[y]['town_share'])]) for y in sorted(ser, reverse=True)],
            note='DESE’s End of Year Financial Report, district totals: what was spent, by the '
                 'fund that paid it. Actual spending, not budgets.')]),
        chart=TP.series('General fund share of school spending', [C.fy(y) for y in sorted(ser)], [
            TP.track('Paid by the general fund', [ser[y]['town_share'] for y in sorted(ser)])], '%',
            note='DESE’s End of Year Financial Report: what was spent, by the fund that paid it. '
                 'The rest is grants and revolving funds.'),
        sources=S('eoyr', 'p-grants'),
        finding_figures=d)
    if lo_sh['town_share'] > ser[f0]['town_share'] + 1e-9:
        fail('the share’s low is no longer its first year')

    # ================================================================ the hub
    h = {}
    h['h-sec'] = fact('h-sec', N(b['sections'], 'course sections'), 'published',
                      'high school sections, {y}; {a} in {y0}', y=SY(b['sy']),
                      a=N(a['sections']), y0=SY(a['sy']))
    h['h-lang'] = fact('h-lang', SHARE(h1['share']), 'published',
                       'of the high school took a language, {y}', y=SY(h1['sy']))
    h['h-hist'] = fact('h-hist', SHARE(now['participation']), 'published',
                       'took history, average {a} to {b}', **E(now))
    h['h-ap'] = fact('h-ap', N(r1['takers'], 'students'), 'published',
                     'sat at least one AP exam, {y}', y=SY(y1))
    h['h-pass'] = fact('h-pass', SHARE(r1['pass_share']), 'published',
                       'of AP tests scored 3 to 5, {y}', allow=('3', '5'), y=SY(y1))
    h['h-named'] = fact('h-named', N(tot['reductions'], 'reductions named'), 'published',
                        'reductions the district named, {c} cycles', c=N(tot['cycles']))
    h['h-blind'] = fact('h-blind', N(tot['blind'], 'adopted cuts'), 'published',
                        'of {m} adopted cuts no series can test', m=N(tot['measurable']))
    h['h-saved'] = fact('h-saved', N(f25['saved'], 'positions'), 'published',
                        'posts the {d} override took off the list', d=vote_day)
    h['h-zero'] = fact('h-zero', N(T['returned'], 'budget lines'), 'published',
                       'of {e} lines cut to zero funded again', e=N(T['events']))
    h['h-replaced'] = fact('h-replaced', PCT(rep_share), 'estimate',
                           'of the {y} grant fall replaced from the general fund', y=FY(ly))
    h['h-town'] = fact('h-town', PCT(ser[f1]['town_share']), 'published',
                       'of school spending from the general fund, {y}', y=FY(f1))
    h['h-outcome'] = gap('h-outcome', 'which posts named for cutting were removed', POSITIONS)
    hub_ladder = LD.ladder([
        LD.tier('What ran', [h['h-sec'], h['h-lang'], h['h-hist'], h['h-ap'], h['h-pass']]),
        LD.tier('What was cut', [h['h-named'], h['h-blind'], h['h-saved'], h['h-zero'],
                                 h['h-outcome']]),
        LD.tier('When grants end', [h['h-replaced'], h['h-town']]),
    ], [
        hcon('The high school ran {a} sections in {y}, more than in {y0}, on flat enrolment.',
             ['h-sec'], a=N(b['sections']), y=SY(b['sy']), y0=SY(a['sy'])),
        hcon('Languages and history are taken by a smaller share of the school than before.',
             ['h-lang', 'h-hist']),
        hcon('{t} students sat an AP exam in {y}, and {p} of tests scored 3 or better.',
             ['h-ap', 'h-pass'], allow=('3',), t=N(r1['takers']), y=SY(y1),
             p=SHARE(r1['pass_share'])),
        hcon('A cut list is intent: {b} of {m} adopted cuts name a job no series counts.',
             ['h-named', 'h-blind', 'h-saved', 'h-outcome'], b=N(tot['blind']),
             m=N(tot['measurable'])),
        hcon('Most school lines cut to zero came back: {r} of {e}.', ['h-zero'],
             r=N(T['returned']), e=N(T['events'])),
        hcon('When grants fell in {y}, the general fund replaced {s} of the fall.',
             ['h-replaced', 'h-town'], y=FY(ly), s=PCT(rep_share)),
    ])
    out[HUB] = TP.hub(
        HUB,
        _fmt('Lunenburg High ran more classes in {y} than in {y0}, but a smaller share takes a '
             'language or history. Most announced cuts cannot be checked against any published '
             'count, and most budget lines cut to zero came back.', hd := dict(
                 y=SY(b['sy']), y0=SY(a['sy']))),
        hub_ladder, chart=lang_chart, answer_figures=hd)

    if sorted(k for k in out if k != HUB) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('school programs topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
