#!/usr/bin/env python3
"""SUGGESTED REPORTS: the reports a meeting's discussion shows a need for, merged across
meetings into one register.

    python3 scripts/build_suggested_reports.py          # write sources/data/suggested-reports.csv
    python3 scripts/build_suggested_reports.py --check  # ...and fail if it is stale or a slug is unknown

WHY. TJ, 15 October 2026: *"after we process all minutes (official and transcript) i want the
processor to identify potential TOPICS/reports to create based on the topics discussed.
naturally if a thread exists, that's great. but other reports might be helpful to do some
research, if we have numbers and data for things in discussion, but dont yet have a report.
Then, make all those suggested reports logged somewhere central, with the meetings
associated. we can share the 'suggested' topic pages across meetings to capture when it
would have helped in many meetings."*

WHERE A SUGGESTION COMES FROM. The read of each recording that already happens
(write_recording_minutes.py, one sonnet call) returns `suggested_reports` beside the votes.
No extra model call per meeting. The recording is read rather than the town's minutes
because a recording carries the discussion and the questions; minutes are a clerk's summary.

HOW SUGGESTIONS MERGE ACROSS MEETINGS -- deterministic, and reviewable.
  1. The model is SHOWN every page that exists (topic registry, threads, analyses) and every
     slug already in this register, and told to reuse one when the subject is the same. It
     names an existing page in `existing` (e.g. `topic:cost-per-sport`) and its own `slug`.
  2. Here, nothing the model says is trusted as an address: an `existing` that is not a real
     page right now is cleared, and the suggestion is filed as new.
  3. Rows are keyed on the existing page where there is one, else on the slug -- so two
     meetings that name the same page merge whatever slugs they chose.
  4. `sources/data/suggested-reports-merges.csv` (from_slug, into_slug, reason) is where a
     PERSON folds two slugs the model named differently. Read here, applied before grouping.
A merge is therefore always one of: same page, same slug, or a line a person wrote.

REPORTS SERVE THREADS; A THREAD DOES NOT ANSWER A REPORT. TJ, 15 October 2026: *"reports should
assist threads."* A thread follows a matter across meetings -- who discussed it, what was
voted, what is next. A report lays out the numbers behind it. So:
  - a suggestion is `exists` only when a TOPIC or ANALYSIS page answers it (`answered_by`);
  - a THREAD it belongs to is recorded in `threads` and the suggestion stays `new` -- it is a
    report that thread needs, and build_threads.py lists it on the thread's page;
  - the thread link is found TWO ways and both are recorded: the model naming the thread
    (`named`), and the thread's own match/qualify/exclude patterns from threads.csv run over
    the suggestion's title, question and words as heard (`words`) -- the same patterns that
    put a minute or an agenda item on the thread, so a suggestion reaches a thread by the
    same rule everything else does.

THREE STATES (rule 13c). A minutes file without `suggested_reports` was never asked; one with
`[]` was asked and the meeting suggested nothing. The register counts both, separately.

WHAT `data_leads` IS. Files in sources/data/ whose NAME shares a word with the suggestion --
a place to start looking, found by string match. It is not a statement that the data
answers the question; `not established` says no file name matched, not that no data exists.
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
OUT = os.path.join(ROOT, 'sources', 'data', 'suggested-reports.csv')
# ONE ROW PER MEETING A SUGGESTION CAME UP IN. TJ, 15 October 2026: "make sure the suggested
# reports include relationships to meetings and dates. suggested reports from 2 years ago are
# interesting, but should have context." So every raising keeps its own date, board, fiscal
# year, the question AS IT WAS ASKED THEN, the words as heard and where to watch them -- a
# merged row's single `question` is the latest one, and an old raising must not be read in
# today's words.
MEETINGS_OUT = os.path.join(ROOT, 'sources', 'data', 'suggested-reports-meetings.csv')
MERGES = os.path.join(ROOT, 'sources', 'data', 'suggested-reports-merges.csv')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
THREADS = os.path.join(ROOT, 'sources', 'data', 'threads.csv')
ANALYSES = os.path.join(ROOT, 'sources', 'analyses')
SINCE = '2026-10-15'

FIELD = {'type': 'array', 'items': {
    'type': 'object', 'additionalProperties': False,
    'required': ['slug', 'title', 'question', 't', 'words_as_heard', 'data_in_play', 'existing'],
    'properties': {
        'slug': {'type': 'string', 'description': 'kebab-case id; REUSE a slug from the SUGGESTED ALREADY list when the subject is the same'},
        'title': {'type': 'string', 'description': 'two to four words, a noun phrase naming the subject ("Ambulance billing revenue"); never a question or a sentence'},
        'question': {'type': 'string', 'description': 'the question the board or the public was asking, in one plain sentence'},
        't': {'type': 'integer', 'description': 'the second the discussion that shows the need begins'},
        'words_as_heard': {'type': 'string', 'description': 'the words that show it was asked or discussed, exactly as the captions render them, under 200 characters'},
        'data_in_play': {'type': 'array', 'items': {'type': 'string'}, 'description': 'figures, documents or data sources that came up, as heard ("the five-year enrollment projection", "fifteen hundred")'},
        'existing': {'type': 'string', 'description': 'the id of an EXISTING page from the list that already answers this (e.g. "topic:cost-per-sport", "thread:stormwater-fee", "analysis:free-cash"), or "" if none does'},
    }},
    'description': 'reports or topic pages this discussion shows a need for; empty if none'}

RULE = """=== SUGGESTED REPORTS, returned as `suggested_reports` ===
A public budget website explains the town's money to residents. From this meeting, name the REPORTS that would have helped the people in the room -- a question the board or the public raised about money, staffing, a service, a building or a decision, where numbers or documents were in play and a page laying them out would have answered it.
- At most four, the most useful first. A meeting that spends real time on money, a building, zoning, a contract or a service usually raises at least one; a purely procedural meeting raises none, and then the list is empty. Do not suggest a report about the meeting itself, a person, or a procedure.
- `title`: two to four words, a noun phrase -- never a question, never a sentence, never a finding.
- If a topic or analysis page in EXISTING PAGES already answers it, put its id in `existing` and reuse its id's last part as `slug`. A THREAD does not answer a report: it follows a matter across meetings, and the report lays out the numbers behind it. If the subject belongs to a thread, put the thread's id in `existing` AND still name the report the thread needs, with its own `slug` and `title`. If a slug in SUGGESTED ALREADY is the same subject, reuse that slug exactly. Only otherwise coin a new kebab-case slug.
- `words_as_heard` exactly as the captions render them; figures in `data_in_play` as heard."""


def _csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def existing():
    """Every page that exists today: {'topic:<id>': {title, url}, 'thread:<id>': ..., 'analysis:<id>': ...}."""
    import topics as T
    out = {}
    for tid, (title, home, _gen) in sorted(T.TOPICS.items()):
        out['topic:' + tid] = {'title': title, 'url': '/%s/%s' % (home, tid)}
    for r in _csv(THREADS):
        out['thread:' + r['id']] = {'title': r['label'], 'url': '/threads/' + r['id']}
    for p in sorted(glob.glob(os.path.join(ANALYSES, '*.md'))):
        aid = os.path.basename(p)[:-3]
        first = next((ln[2:].strip() for ln in open(p, encoding='utf-8') if ln.startswith('# ')), aid)
        out['analysis:' + aid] = {'title': first, 'url': '/analysis/' + aid}
    return out


def prompt_context():
    """The block the minutes prompt carries, so the model can reuse a page or a slug."""
    ex = existing()
    reg = _csv(OUT)
    lines = ['EXISTING PAGES (id — title):'] + ['- %s — %s' % (k, v['title']) for k, v in ex.items()]
    lines += ['', 'SUGGESTED ALREADY (slug — title):']
    lines += ['- %s — %s' % (r['slug'], r['title']) for r in reg if r['status'] == 'new'] or ['- none yet']
    return '\n'.join(lines)


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')


STOP = set('the and for with from that this what town lunenburg school schools budget cost costs report fund funds data year years'.split())


def words(s):
    return {w for w in re.findall(r'[a-z0-9]+', (s or '').lower()) if len(w) >= 4 and w not in STOP}


def data_leads(title, slug):
    want = words(title) | words(slug.replace('-', ' '))
    hits = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'sources', 'data', '*.csv'))):
        name = os.path.basename(p)
        if name.startswith('suggested-reports'):
            continue
        if want & words(name[:-4].replace('-', ' ')):
            hits.append(name)
    return hits


def compile_threads():
    out = []
    for t in _csv(THREADS):
        c = lambda k: re.compile(t[k], re.I) if (t.get(k) or '').strip() else None
        out.append((t['id'], c('match'), c('qualify'), c('exclude')))
    return out


def threads_for(text, compiled):
    """Thread ids whose own patterns find this text: match, and qualify if the thread has one,
    and not exclude. No board-only route: a suggestion is about a subject, not a board."""
    hits = []
    for tid, rx, qu, ex in compiled:
        if rx and rx.search(text) and (not qu or qu.search(text)) and not (ex and ex.search(text)):
            hits.append(tid)
    return hits


def build():
    ex = existing()
    tpat = compile_threads()
    merges = {r['from_slug']: r['into_slug'] for r in _csv(MERGES)}
    rows = collections.OrderedDict()
    looked = not_looked = 0
    cleared = []
    occ = []
    for f in sorted(glob.glob(os.path.join(MINUTES, '*', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        mm = m.get('minutes') or {}
        if 'suggested_reports' not in mm:
            not_looked += 1
            continue
        looked += 1
        for s in mm['suggested_reports']:
            slug = slugify(s.get('slug') or s.get('title'))
            slug = merges.get(slug, slug)
            exk = (s.get('existing') or '').strip()
            if exk and exk not in ex:
                cleared.append('%s: %r is not a page' % (os.path.relpath(f, ROOT), exk))
                exk = ''
            # A THREAD IS NOT AN ANSWER. Named by the model, it is the matter this report
            # would serve; the report itself is still to write.
            named = [exk.split(':', 1)[1]] if exk.startswith('thread:') else []
            if named:
                exk = ''
                if slug == named[0]:
                    slug = slugify(s.get('title'))
                    slug = merges.get(slug, slug)
            text = ' '.join(str(s.get(k) or '') for k in ('title', 'question', 'words_as_heard'))
            by_words = threads_for(text, tpat)
            tlinks = sorted(set(named) | set(by_words))
            key = exk or ('new:' + slug)
            r = rows.setdefault(key, {'id': key, 'slug': exk.split(':', 1)[1] if exk else slug,
                                      'titles': collections.Counter(), 'questions': [], 'cites': [],
                                      'boards': set(), 'dates': [], 'data': [], 'meetings': set(),
                                      'threads': {}})
            for tid in tlinks:
                how = r['threads'].setdefault(tid, set())
                how.update(['named'] if tid in named else [])
                how.update(['words'] if tid in by_words else [])
            r['titles'][s.get('title', '').strip()] += 1
            r['questions'].append((m['meeting_date'], s.get('question', '').strip()))
            r['meetings'].add((m['board_slug'], m['meeting_date']))
            r['boards'].add(m['board_slug'])
            r['dates'].append(m['meeting_date'])
            r['cites'].append('%s %s %s&t=%ds' % (m['board_slug'], m['meeting_date'], m['video_url'], int(s.get('t') or 0)))
            r['data'] += [d for d in s.get('data_in_play') or [] if d not in r['data']]
            t = int(s.get('t') or 0)
            occ.append({
                'id': key, 'slug': exk.split(':', 1)[1] if exk else slug,
                'date': m['meeting_date'], 'fiscal_year': fiscal_year(m['meeting_date']),
                'board_slug': m['board_slug'], 'board': m.get('board') or m['board_slug'],
                'title_as_suggested': (s.get('title') or '').strip(),
                'question_then': (s.get('question') or '').strip(),
                'words_as_heard': (s.get('words_as_heard') or '').strip(),
                'data_in_play_as_heard': ' | '.join(s.get('data_in_play') or []),
                'watch_at': '%s&t=%ds' % (m['video_url'], t), 'at': '%d:%02d:%02d' % (t // 3600, t // 60 % 60, t % 60),
                'our_minutes': '/meeting-minutes/%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
                'threads': ';'.join(tlinks),
            })
    out = []
    for key, r in rows.items():
        is_ex = not key.startswith('new:')
        title = ex[key]['title'] if is_ex else sorted(r['titles'].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        leads = data_leads(title, r['slug'])
        out.append({
            'id': key, 'slug': r['slug'], 'title': title,
            'status': 'exists' if is_ex else 'new',
            'exists_at': ex[key]['url'] if is_ex else '',
            'threads': ';'.join('%s (%s)' % (tid, '+'.join(sorted(how))) for tid, how in sorted(r['threads'].items())),
            'meetings': len(r['meetings']),
            'boards': ';'.join(sorted(r['boards'])),
            'first': min(r['dates']), 'last': max(r['dates']),
            'fiscal_years': ';'.join(sorted({fiscal_year(d) for d in r['dates']})),
            'meeting_list': ' | '.join('%s %s' % (d, b) for b, d in sorted(r['meetings'], key=lambda x: x[1], reverse=True)),
            'question': sorted(r['questions'])[-1][1],
            'citations': ' | '.join(sorted(set(r['cites']), reverse=True)),
            'data_in_play_as_heard': ' | '.join(r['data'][:12]),
            'data_leads': ';'.join(leads[:8]) or 'not established',
        })
    out.sort(key=lambda x: (-x['meetings'], x['status'] != 'new', x['id']))
    occ.sort(key=lambda o: (o['id'], o['date'], o['board_slug']), reverse=False)
    return out, looked, not_looked, cleared, occ


def fiscal_year(date):
    """Massachusetts fiscal year of a meeting date: FY2027 runs 1 July 2026 to 30 June 2027."""
    y, mo = int(date[:4]), int(date[5:7])
    return 'FY%d' % (y + 1 if mo >= 7 else y)


COLS = ['id', 'slug', 'title', 'status', 'exists_at', 'threads', 'meetings', 'boards', 'first', 'last',
        'fiscal_years', 'meeting_list', 'question', 'citations', 'data_in_play_as_heard', 'data_leads']
MEETING_COLS = ['id', 'slug', 'date', 'fiscal_year', 'board_slug', 'board', 'title_as_suggested',
                'question_then', 'words_as_heard', 'data_in_play_as_heard', 'at', 'watch_at',
                'our_minutes', 'threads']


def render(rows, cols=COLS):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return b.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, looked, not_looked, cleared, occ = build()
    outs = {OUT: render(rows), MEETINGS_OUT: render(occ, MEETING_COLS)}
    for c in cleared:
        print('  existing page cleared -- ' + c)
    if a.check:
        for path, text in outs.items():
            have = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if have != text:
                sys.exit('%s is stale: run scripts/build_suggested_reports.py' % os.path.basename(path))
        print('suggested reports: %d row(s), current; %d meeting(s) read for suggestions, %d never asked'
              % (len(rows), looked, not_looked))
        return 0
    for path, text in outs.items():
        tmp = path + '.tmp'
        open(tmp, 'w', encoding='utf-8').write(text)
        os.replace(tmp, path)
    print('wrote %s: %d suggestion(s) (%d new, %d would have helped from a page that exists); '
          '%d meeting(s) read for suggestions, %d never asked'
          % (os.path.relpath(OUT, ROOT), len(rows), sum(r['status'] == 'new' for r in rows),
             sum(r['status'] == 'exists' for r in rows), looked, not_looked))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
