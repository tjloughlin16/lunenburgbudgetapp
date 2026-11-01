#!/usr/bin/env python3
"""Read each dumped TOWN officials/staff page into entries, one isolated model call per page.

Input: `sources/data/town-rosters/<edition>-p<NNN>.txt` from `dump_town_roster_pages.py`.
Output: `<edition>-p<NNN>.json` beside it -- every entry tied to the numbered line it was
read from, every heading and every non-entry line claimed, so `build_town_rosters.py` can
do line accounting.

**Why a model, and why one page at a time.** The directory is printed in columns whose
headings sit in one row with the names in rows beneath, and the layout changes every
edition (rule 13c). Placing each name under its heading from the `@NN` positions is a
reading task, not a pattern. It has no dependency on any conversation, so it runs in
isolation (`claude_lean`, CLAUDE.md 7g): the page text, the heading still open at the foot
of the previous page, and nothing else.

**What is checked here, before anything is written.** Line numbers in range; every line
claimed; every name's words present on the line it was attributed to. A page failing any
of those gets ONE retry with the failures listed, and is written either way with its
failures recorded -- the builder refuses to publish a page that does not account.

    python3 scripts/read_town_roster_pages.py --edition 1965 [--model sonnet] [--force]
    python3 scripts/read_town_roster_pages.py --all [--jobs 4]
"""

import argparse
import concurrent.futures as cf
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claude_lean  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'sources', 'data', 'town-rosters')
PAGES = os.path.join(DIR, 'PAGES.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = os.environ.get('TOWN_ROSTER_MODEL', 'sonnet')
TIMEOUT = 900

WHY = ['page-furniture', 'not-a-town-office', 'vacancy', 'prose-or-schedule', 'continuation']

SCHEMA = {
    'type': 'object',
    'required': ['entries', 'headings', 'ignored', 'open_at_foot'],
    'properties': {
        'entries': {'type': 'array', 'items': {
            'type': 'object',
            'required': ['line', 'name', 'position', 'section', 'term', 'note'],
            'properties': {
                'line': {'type': 'integer'},
                'name': {'type': 'string'},
                'position': {'type': 'string'},
                'section': {'type': 'string'},
                'term': {'type': 'string'},
                'note': {'type': 'string'}}}},
        'headings': {'type': 'array', 'items': {'type': 'integer'}},
        'ignored': {'type': 'array', 'items': {
            'type': 'object', 'required': ['line', 'why'],
            'properties': {'line': {'type': 'integer'},
                           'why': {'type': 'string', 'enum': WHY}}}},
        'open_at_foot': {'type': 'object', 'required': ['section', 'position'],
                         'properties': {'section': {'type': 'string'},
                                        'position': {'type': 'string'}}},
    }}

SYSTEM = """You read one page of a Massachusetts town annual report that lists TOWN OFFICIALS
(elected and appointed officers, boards, committees, commissions) and sometimes department
staff. The page is given as numbered lines. Each printed run is prefixed with @NN, its left
edge as a percentage of page width. The lists are printed in COLUMNS: a heading such as
"Board of Selectmen" or "PLANNING BOARD" governs the names printed BELOW it at about the same
@NN, until the next heading in that column. Several columns share each printed line, so one
line can hold names belonging to different headings. Use the @NN positions to put every name
under the right heading. A heading can also continue from the previous page (given below as
OPEN AT THE TOP OF THIS PAGE).

Return JSON:
- entries: one per PERSON per position. For each:
  line: the number of the line the NAME is printed on.
  name: the person's name exactly as printed on that line (keep OCR misspellings and titles
    such as Mrs., Dr., Jr., 2nd; DROP a leading or trailing term year and any trailing
    affiliation text). Never correct or complete a name from knowledge.
  position: the office/board/committee heading governing the name, verbatim as printed
    (e.g. "Board of Selectmen", "AGRICULTURAL COMMISSION- 3 year terms", "Police Sergeant").
    If the name line itself carries the role ("Steven Archambault-Town Moderator Designee"
    under a committee heading), position is still the committee and the role goes in note.
  section: the printed SECTION heading governing the position, verbatim -- e.g. "Elected",
    "Appointed", "ELECTED OFFICIALS", "APPOINTED TOWN OFFICIALS", "FY'05 APPOINTMENT LIST",
    "SPECIAL COMMITTEES APPOINTED 1965", "Appointed by Governor:". Inherit it from earlier
    on the page or from the previous page. Empty string only if none is printed anywhere.
  term: the term year or term text printed with this name ("1967", "2020", "2019- Resigned
    March 2018"), verbatim; empty if none.
  note: any other text printed with the name (affiliation, "(resigned)", "(appointed
    October)", "Chairman", "Ex Officio"); empty if none. A note printed on its own line
    directly under a name belongs to that name, and its line is listed in ignored with
    why "continuation".
- headings: line numbers of every line that holds a heading (section, office, board, column
  title, "Members:", "TERM EXPIRES"). A line can be both a heading line and a name line.
- ignored: every other line that is not a name of a town official/employee, with why:
  page-furniture (page numbers, running titles, "TERMS ARE FOR ONE YEAR UNLESS...");
  not-a-town-office (United States senators, congressmen, governor and other state
    officers, state senators and representatives, county officers -- these people are NOT
    entries);
  vacancy ("Vacancy", "1 Vacancy" -- not a person, not an entry);
  prose-or-schedule (narrative text, office hours, meeting schedules, census facts);
  continuation (a wrapped part of a name's note or of a heading printed on its own line).
- open_at_foot: the section and position still open at the bottom of the page (so the next
  page can continue it).

DEPARTMENT PAGES (marked "department list" in the page header) are department reports that
carry a staff roster (fire, police, auxiliary police...). The roster members are entries: position
is the rank or title printed with or above the name ("Lieutenant", "Call Firefighters",
"Patrolman"), section is the roster's printed heading ("ROSTER OF FIREFIGHTERS OF 1990",
"Department Personnel:", or the department heading such as "POLICE" or "FIRE"). Names that only
appear inside running prose sentences are NOT entries (their lines are prose-or-schedule).
Drop leading asterisks or similar markers from a name; if the page prints a legend for the
marker, put its meaning in note.

Every line number from 1 to the last line must appear in entries, headings or ignored.
A name followed by a different name on the same line is two entries. A person listed under
two headings is two entries. Do not invent anything not printed."""


def plan():
    rows = list(csv.DictReader(open(PAGES, newline='', encoding='utf-8')))
    by = {}
    for r in rows:
        by.setdefault(r['edition'], []).append(r)
    for ed in by:
        by[ed].sort(key=lambda r: int(r['page']))
    return by


def numbered(path):
    out = {}
    for raw in open(path, encoding='utf-8'):
        m = re.match(r'\s*(\d+)\| ?(.*)$', raw.rstrip('\n'))
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def tokens(text):
    return re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text or '')


def problems(body, lines):
    """Unclaimed or out-of-range lines, and names whose words are not on their line."""
    total = len(lines)
    claimed = set()
    out = []
    for e in body.get('entries', []):
        n = e.get('line')
        if not isinstance(n, int) or n < 1 or n > total:
            out.append('entry %r has line %r, outside 1..%d' % (e.get('name'), n, total))
            continue
        claimed.add(n)
        here = re.sub(r'@\d\d', ' ', lines[n]).lower()
        missing = [t for t in tokens(e.get('name')) if t.lower() not in here]
        if missing:
            out.append('line %d: name %r -- %s not printed on that line (%r)'
                       % (n, e.get('name'), missing, lines[n][:90]))
    for n in body.get('headings', []):
        if isinstance(n, int) and 1 <= n <= total:
            claimed.add(n)
    for g in body.get('ignored', []):
        n = g.get('line')
        if isinstance(n, int) and 1 <= n <= total:
            claimed.add(n)
    gone = sorted(set(range(1, total + 1)) - claimed)
    if gone:
        out.append('lines never claimed: %s' % gone)
    return out


def relocate(body, lines):
    """An entry whose name is not on its line but is wholly on the line directly above or
    below -- and on only one of them -- is moved there. The model's line numbers drift by
    one on dense pages (1990 p5 put `Alan Paton` on 26; he is printed on 27). The move is
    made by evidence, recorded on the page as `relocated`, and anything else stays a fault."""
    moved = []
    for e in body.get('entries', []):
        n = e.get('line')
        toks = [t.lower() for t in tokens(e.get('name'))]
        if not isinstance(n, int) or not toks or n not in lines:
            continue
        here = lambda k: re.sub(r'@\d\d', ' ', lines.get(k, '')).lower()  # noqa: E731
        if all(t in here(n) for t in toks):
            continue
        near = [k for k in (n - 1, n + 1) if k in lines and all(t in here(k) for t in toks)]
        if len(near) == 1:
            moved.append({'name': e.get('name'), 'from': n, 'to': near[0]})
            e['line'] = near[0]
    return moved


def call(model, prompt):
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = claude_lean.run(['claude', '-p', '--tools', '', '--model', model,
                         '--system-prompt', SYSTEM, '--json-schema', json.dumps(SCHEMA),
                         '--output-format', 'json', '--max-budget-usd', '2'],
                        input=prompt, capture_output=True, text=True, env=env,
                        timeout=TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr)[-1500:])
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    return body, float(res.get('total_cost_usd') or 0)


def read_page(row, carry, model, force):
    ed, page = row['edition'], int(row['page'])
    txt = os.path.join(DIR, '%s-p%03d.txt' % (ed, page))
    out = txt[:-4] + '.json'
    if os.path.exists(out) and not force:
        held = json.load(open(out, encoding='utf-8'))
        return held, 0.0, 'held'
    lines = numbered(txt)
    head = open(txt, encoding='utf-8').read()
    prompt = ('OPEN AT THE TOP OF THIS PAGE (from the previous page): section=%r position=%r\n\n'
              '%s' % (carry.get('section', ''), carry.get('position', ''), head))
    cost, moved = 0.0, []
    body, c = call(model, prompt)
    cost += c
    bad = problems(body, lines)
    tries = 1
    if bad and lines:
        retry = prompt + ('\n\nYOUR PREVIOUS ANSWER HAD THESE FAULTS -- fix them and answer '
                          'again in full:\n- ' + '\n- '.join(bad[:40]) +
                          '\n\nPREVIOUS ANSWER:\n' + json.dumps(body)[:30000])
        body2, c = call(model, retry)
        cost += c
        tries = 2
        bad2 = problems(body2, lines)
        if len(bad2) <= len(bad):
            body, bad = body2, bad2
    moved = relocate(body, lines)
    if moved:
        bad = problems(body, lines)
    doc = {
        'warning': 'TOWN OFFICIALS AS THE ANNUAL REPORT PRINTS THEM, placed under their '
                   'headings by a language model from the numbered page text. The page is '
                   'the record; every name is checked against the line it was read from.',
        'document': row['document'], 'edition': ed, 'page': page, 'list': row['list'],
        'lines_on_page': len(lines), 'carried_in': carry,
        'entries': body.get('entries', []), 'headings': body.get('headings', []),
        'ignored': body.get('ignored', []), 'open_at_foot': body.get('open_at_foot', {}),
        'relocated': moved, 'faults': bad, 'model': model, 'tries': tries, 'cost_usd': round(cost, 5),
    }
    with open(out + '.tmp', 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    os.replace(out + '.tmp', out)
    return doc, cost, 'read'


def read_edition(ed, rows, model, force):
    carry, cost, notes = {}, 0.0, []
    for row in rows:
        try:
            doc, c, how = read_page(row, carry, model, force)
        except Exception as e:  # noqa: BLE001 -- reported, the next run retries
            notes.append('%s p%s FAILED: %s' % (ed, row['page'], str(e)[-300:]))
            carry = {}
            continue
        cost += c
        carry = doc.get('open_at_foot') or {}
        notes.append('%s p%s %s: %d entries, %d faults, $%.3f'
                     % (ed, row['page'], how, len(doc['entries']), len(doc['faults']), c))
    return ed, cost, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edition', action='append')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--model', default=MODEL)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--jobs', type=int, default=3)
    args = ap.parse_args()
    by = plan()
    eds = sorted(by) if args.all else (args.edition or [])
    if not eds:
        ap.error('name --edition or --all')
    total = 0.0
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = [ex.submit(read_edition, ed, by[ed], args.model, args.force) for ed in eds]
        for f in cf.as_completed(futs):
            ed, cost, notes = f.result()
            total += cost
            for n in notes:
                print(n, flush=True)
    print('cost this run: $%.3f (API-equivalent)' % total)


if __name__ == '__main__':
    main()
