#!/usr/bin/env python3
"""STEP 4 OF notes/PLAN-EVERYTHING-IN-THE-REPORTS.md: sort the FY2011-FY2025 catalogue entries
that sit on pages no dataset of ours reads.

    python3 scripts/sort_catalogue.py --dry-run          # the set, the exclusions, the prompts; no calls
    python3 scripts/sort_catalogue.py                    # one claude -p run per edition not yet written
    python3 scripts/sort_catalogue.py --edition FY2014 --redo
    python3 scripts/sort_catalogue.py --check            # validate the written CSV, no calls

Writes sources/data/annual-report-catalogue-sort.csv, one row per entry:
  edition, name, pages, verdict, dataset, reason, decided_by, decided_on

VERDICTS. `repeat` -- the table is already held for THIS edition by the dataset named (printed
twice, or read from another page). `prose` -- not data worth a dataset (contents pages, office
hours, narrative). `gap` -- real data we hold none of for this edition; `dataset` is filled when
an existing dataset is the family it would extend (held for other years, not this one).
`unsure` -- the description cannot decide it. `deferred-to-list-survey` -- a list of PEOPLE
(officials, board and committee members, staff), left to step 3; decided here by a fixed rule
on `grain` and `name` (LIST_GRAIN, LIST_NAME), with no model call.

WHAT A VERDICT IS. A judgement made from the catalogue's DESCRIPTION of a table -- its
what_it_is, grain, columns and notes -- against the NAMES of our datasets and the pages each
reads. No page text is read. So `gap` means "nothing we hold looks like this", not a proof that
the town's figures are absent from our holdings (CLAUDE.md 13c): it is where to look next.

THE SET is recomputed every run from build_annual_report_coverage.py (editions(),
scan_datasets(), the same page-overlap test the coverage page uses), because the datasets keep
growing and an entry that was unread yesterday may be read today.

ISOLATION (CLAUDE.md 7g): each edition is one `claude -p` call through claude_lean, sonnet,
JSON schema. Each run is VALIDATED AS IT FINISHES -- every entry answered exactly once, the
verdict in the allowed set, every `repeat` naming a dataset that exists in sources/data -- and
a failure stops the batch. Cost is appended to sources/data/agentic-spend.csv as stream
`catalogue-sort`, board = the edition, date empty (so backlog_pace's meeting audit skips it).
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_annual_report_coverage as B  # noqa: E402
import claude_lean  # noqa: E402

ROOT = B.ROOT
DATA = B.DATA
OUT = os.path.join(DATA, 'annual-report-catalogue-sort.csv')
SPEND = os.path.join(DATA, 'agentic-spend.csv')
CATALOGUE = os.path.join(DATA, 'annual-report-catalogue.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = os.environ.get('CATALOGUE_SORT_MODEL', 'sonnet')
TIMEOUT = 900
FIELDS = ['edition', 'name', 'pages', 'verdict', 'dataset', 'reason', 'decided_by', 'decided_on']
MODEL_VERDICTS = ('repeat', 'prose', 'gap', 'unsure')
DEFERRED = 'deferred-to-list-survey'

# A LIST OF PEOPLE is step 3's (the list survey). Decided by these, never by a model.
LIST_GRAIN = re.compile(
    r'^\s*one\s+(person|committee member|board member|member of|elected official|official|'
    r'office[ -]?holder|officeholder|legislator|trustee|staff member)\b', re.I)
LIST_NAME = re.compile(
    r'elected officials|legislator|membership\b|\btrustees?\b.*\bstaff\b|\bstaff\b.*\broster\b|'
    r'appointed (officials|boards)|officers and committees', re.I)

SCHEMA = {
    'type': 'object',
    'properties': {'entries': {'type': 'array', 'items': {
        'type': 'object',
        'properties': {
            'entry_key': {'type': 'string'},
            'verdict': {'type': 'string', 'enum': list(MODEL_VERDICTS)},
            'dataset': {'type': 'string'},
            'reason': {'type': 'string'},
        },
        'required': ['entry_key', 'verdict', 'dataset', 'reason']}}},
    'required': ['entries'],
}

SYSTEM = """You sort entries in a catalogue of tables printed in one Massachusetts town's annual town report.
Each entry was found on a page that NONE of our datasets reads. For each entry decide ONE verdict:

- repeat: the same table is already held FOR THIS EDITION by one of our datasets (for example the
  table is printed twice in the report, or the dataset holds this content read from another page).
  Put that dataset's exact name in `dataset`. Only use repeat when the dataset holds rows for THIS
  edition and its name and columns make the match plain.
- prose: not data worth a dataset -- a table of contents, office hours, a phone directory, a meeting
  schedule, a narrative passage laid out as a table, a chart that only restates a table we hold.
- gap: real data (figures, counts, amounts, a list of things with attributes) that we hold none of
  for this edition. If one of our datasets is plainly the same family (it holds this kind of table
  for OTHER editions but has no rows for this edition, or does not read these pages), put its name in
  `dataset`; otherwise leave `dataset` empty.
- unsure: the description cannot decide between the above.

Rules: answer every entry exactly once, using its entry_key verbatim. `dataset` must be a name from
the dataset list exactly, or empty. `reason` is ONE short sentence saying what the decision rests on.
You judge from descriptions only; do not claim to have seen the page."""


def today():
    return dt.date.today().isoformat()


def unread():
    """{edition: [catalogue rows on no page a DATA dataset reads]}, plus the dataset scan."""
    known = B.editions()
    ds = B.scan_datasets(known)
    maps = B.read_page_maps(ds)
    out = collections.defaultdict(list)
    onread = collections.defaultdict(list)
    for r in B.read_csv(CATALOGUE):
        ed = B.base_edition(r.get('edition') or '')
        if known.get(ed, {}).get('era') != 'fiscal':
            continue
        (onread if B.on_read_page(r, ed, maps) else out)[ed].append(r)
    return out, onread, ds


def deferred(r):
    return bool(LIST_GRAIN.search(r.get('grain') or '') or LIST_NAME.search(r.get('name') or ''))


def header(name):
    with open(os.path.join(DATA, name + '.csv'), newline='', encoding='utf-8') as fh:
        return next(csv.reader(fh), [])


def prompt(ed, entries, onread, ds):
    L = ['EDITION %s (the annual town report for fiscal year %s).' % (ed, ed[2:]), '']
    L.append('OUR DATASETS (name | rows from this edition | pages read in this edition | '
             'editions held | columns):')
    for n in sorted(ds):
        d = ds[n]
        if d['role'] != 'data':
            continue
        here = d['by_edition'].get(ed, 0)
        pages = ','.join(str(p) for p in sorted(d['pages'].get(ed, ()))) or '-'
        eds = len([e for e in d['by_edition'] if e.startswith('FY')])
        cols = ' '.join(header(n))[:220]
        L.append('- %s | %d | %s | %d FY editions | %s' % (n, here, pages, eds, cols))
    L += ['', 'TABLES IN THIS EDITION ON PAGES WE DO READ (context only, do not answer these):']
    for r in onread:
        L.append('- p%s %s' % (r['pages'], r['name']))
    L += ['', 'ENTRIES TO SORT (answer each):']
    for i, r in enumerate(entries):
        L.append(json.dumps({
            'entry_key': key(ed, i), 'pages': r['pages'], 'name': r['name'],
            'what_it_is': r['what_it_is'], 'grain': r['grain'], 'columns': r['columns'],
            'extractable': r['extractable'], 'notes': r['notes']}, ensure_ascii=False))
    return '\n'.join(L)


def key(ed, i):
    return '%s#%02d' % (ed, i)


def call(text):
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL,
                         '--system-prompt', SYSTEM, '--json-schema', json.dumps(SCHEMA),
                         '--output-format', 'json', '--max-budget-usd', '2'],
                        input=text, capture_output=True, text=True, env=env, timeout=TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr)[-1500:])
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    return body, float(res.get('total_cost_usd') or 0)


def validate(ed, entries, body, existing):
    """Every entry answered exactly once; verdict allowed; a `repeat` names a real dataset."""
    want = {key(ed, i) for i in range(len(entries))}
    got = collections.Counter(e.get('entry_key') for e in body.get('entries', []))
    bad = []
    if set(got) != want:
        bad.append('keys: missing %s, extra %s' % (sorted(want - set(got)), sorted(set(got) - want)))
    bad += ['answered %d times: %s' % (c, k) for k, c in got.items() if c > 1]
    for e in body.get('entries', []):
        if e.get('verdict') not in MODEL_VERDICTS:
            bad.append('%s verdict %r' % (e.get('entry_key'), e.get('verdict')))
        d = (e.get('dataset') or '').strip()
        if e.get('verdict') == 'repeat' and d not in existing:
            bad.append('%s repeat names %r, not a dataset in sources/data' % (e.get('entry_key'), d))
        if d and d not in existing:
            bad.append('%s names %r, not a dataset in sources/data' % (e.get('entry_key'), d))
        if not (e.get('reason') or '').strip():
            bad.append('%s has no reason' % e.get('entry_key'))
    return bad


def read_out():
    return B.read_csv(OUT) if os.path.exists(OUT) else []


def write_out(rows):
    rows = sorted(rows, key=lambda r: (int(r['edition'][2:]), int((re.findall(r'\d+', r['pages']) or [0])[0]), r['name']))
    tmp = OUT + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, OUT)


def spend(ed, cost, result):
    with open(SPEND, 'a', newline='', encoding='utf-8') as fh:
        csv.writer(fh, lineterminator='\n').writerow([
            dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'catalogue-sort',
            ed, '', '%.4f' % cost if cost else '', result])


def existing_datasets():
    return {p[:-4] for p in os.listdir(DATA) if p.endswith('.csv')}


def check():
    """The written CSV against the current set: one row per unread entry, allowed verdicts."""
    un, _, _ = unread()
    have = collections.Counter((r['edition'], r['name'], r['pages']) for r in read_out())
    want = {(B.base_edition(r['edition']), r['name'], r['pages']) for ed in un for r in un[ed]}
    existing = existing_datasets()
    bad = ['answered %d times: %s' % (c, k) for k, c in have.items() if c > 1]
    done = {k[0] for k in have}
    missing = sorted(k for k in want if k[0] in done and k not in have)
    stale = sorted(k for k in have if k not in want)
    for r in read_out():
        if r['verdict'] not in MODEL_VERDICTS + (DEFERRED,):
            bad.append('verdict %r: %s' % (r['verdict'], r['name']))
        if r['verdict'] == 'repeat' and r['dataset'] not in existing:
            bad.append('repeat names %r: %s' % (r['dataset'], r['name']))
    print('%d rows, %d editions; %d entries now unread in those editions have no row; '
          '%d rows are no longer unread (a dataset now reads the page)'
          % (sum(have.values()), len(done), len(missing), len(stale)))
    for k in missing[:20]:
        print('  no row:', k)
    for k in stale[:20]:
        print('  now read:', k)
    for b in bad:
        print('  BAD', b)
    return 1 if bad else 0


STOP = set('the a an of and by in for with to on vs against this year town lunenburg fy calendar '
           'spring may november august june february march'.split())
CONSISTENCY_RULE = 'rule: sort_catalogue.consistency (same table, other year; dataset holds this edition)'


def name_key(name):
    s = re.sub(r'\(.*?\)|--.*$', '', name.lower())
    return ' '.join(w for w in re.sub(r'[^a-z ]', ' ', s).split() if w not in STOP)


def families(rows):
    """Entries that are the SAME TABLE in different years: joined when they share the
    catalogue's `cluster` or a name that is identical once years, dates and stopwords go."""
    cat = {(B.base_edition(r['edition']), r['name'], r['pages']): r for r in B.read_csv(CATALOGUE)}
    par = {}

    def find(x):
        while par.setdefault(x, x) != x:
            x = par[x]
        return x
    for r in rows:
        k = ('k', r['edition'], r['name'], r['pages'])
        par[find(k)] = find(('c', cat[k[1:]]['cluster']))
        par[find(k)] = find(('n', name_key(r['name'])))
    out = collections.defaultdict(list)
    for r in rows:
        out[find(('k', r['edition'], r['name'], r['pages']))].append(r)
    return list(out.values())


def consistency(write):
    """A family whose years disagree. An entry becomes `repeat` when a dataset some member of
    the family names holds rows for THIS edition and records no page for them -- with a page
    recorded, the rows came from another page, so they are another table, and nothing moves.
    Everything else that disagrees is listed, not changed."""
    known = B.editions()
    ds = B.scan_datasets(known)
    rows = read_out()
    changed, unsettled = [], []
    for fam in families(rows):
        vs = {r['verdict'] for r in fam} - {DEFERRED}
        if len(vs) < 2:
            continue
        named = {r['dataset'] for r in fam if r['dataset']}
        for r in fam:
            if r['verdict'] in ('repeat', DEFERRED):
                continue
            hit = [n for n in sorted(named) if n in ds and ds[n]['by_edition'].get(r['edition'])
                   and not ds[n]['pages'].get(r['edition'])]
            if hit:
                changed.append((dict(r), hit[0]))
                r.update(verdict='repeat', dataset=hit[0], decided_by=CONSISTENCY_RULE,
                         decided_on=today(),
                         reason='same table as another year; %s holds %d rows for this edition, '
                                'with no page recorded' % (hit[0], ds[hit[0]]['by_edition'][r['edition']]))
        if len({r['verdict'] for r in fam} - {DEFERRED, 'repeat'}) > 1:
            unsettled.append(sorted(fam, key=lambda r: int(r['edition'][2:])))
    for old, d in changed:
        print('-> repeat %s p%s %s (was %s)' % (old['edition'], old['pages'], old['name'], old['verdict']))
    for fam in unsettled:
        print('UNSETTLED: ' + '; '.join('%s %s' % (r['edition'], r['verdict']) for r in fam)
              + ' | ' + fam[0]['name'])
    if write:
        write_out(rows)
    return 0


# RULE 13c, applied to `prose`. A table whose counts our reading lost is not prose. Every
# `prose` verdict whose description mentions any of these is re-sorted WITH THE PAGE TEXT.
COUNTY = re.compile(r'\b(counts?|cases?|figures?|numbers?|numeric|table)\b', re.I)
PAGES_DIR = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
PAGE_CAP = 6000
RECHECK_SYSTEM = SYSTEM + """

THIS IS A RE-CHECK. Each entry was first called `prose` from its description alone. You now also
get the page text, from the layout-preserving OCR reading of the report where we have one. RULE:
a table whose counts or figures our reading FAILED to capture is not prose -- if the description
or the page shows the table printed figures, say `gap` (or `repeat`) when the figures are legible
in the page text, and `unsure` when they are not. Keep `prose` only for things that are not data
whatever the reading: a table of contents, office hours, a phone directory, regulatory text laid
out as a table, a heading with no table under it."""


def page_text(ed, pages):
    """The layout OCR of those pages (FY<year>.ocr.txt), else the report's text layer."""
    want = sorted({int(p) for p in re.findall(r'\d+', pages)})
    want = list(range(want[0], want[-1] + 1)) if ', ' not in pages and len(want) == 2 else want
    for path in (os.path.join(PAGES_DIR, '%s.ocr.txt' % ed), os.path.join(PAGES_DIR, '%s.txt' % ed)):
        if not os.path.exists(path):
            continue
        out, keep = [], False
        for line in open(path, encoding='utf-8', errors='replace'):
            m = re.match(r'^===PAGE (\d+)===', line)
            if m:
                keep = int(m.group(1)) in want
            if keep:
                out.append(re.sub(r' {3,}', '   ', line.rstrip()))
        if out:
            text = '\n'.join(out)
            return text[:PAGE_CAP] + ('\n[... cut at %d chars]' % PAGE_CAP if len(text) > PAGE_CAP else ''), \
                os.path.relpath(path, ROOT)
    return '', ''


def recheck_prose(runs_left, dry):
    cat = {(B.base_edition(r['edition']), r['name'], r['pages']): r for r in B.read_csv(CATALOGUE)}
    rows = read_out()
    pick = [r for r in rows if r['verdict'] == 'prose' and COUNTY.search(' '.join(
        cat[(r['edition'], r['name'], r['pages'])][c] for c in ('what_it_is', 'grain', 'columns', 'notes')))]
    if not pick:
        print('nothing to re-check')
        return 0
    _, _, ds = unread()
    names = sorted(n for n, d in ds.items() if d['role'] == 'data')
    existing = existing_datasets()
    n = min(runs_left, 3)
    size = -(-len(pick) // n)
    total = 0.0
    for b in range(0, len(pick), size):
        batch = pick[b:b + size]
        L = ['OUR DATASETS, with the FY editions each holds rows for:']
        for nm in names:
            L.append('- %s: %s' % (nm, ','.join(sorted(e for e in ds[nm]['by_edition'] if e.startswith('FY'))) or 'no FY rows'))
        L += ['', 'ENTRIES TO RE-SORT (answer each):']
        for i, r in enumerate(batch):
            c = cat[(r['edition'], r['name'], r['pages'])]
            txt, src = page_text(r['edition'], r['pages'])
            L.append(json.dumps({'entry_key': 'R#%02d' % i, 'edition': r['edition'], 'pages': r['pages'],
                                 'name': r['name'], 'what_it_is': c['what_it_is'], 'grain': c['grain'],
                                 'columns': c['columns'], 'notes': c['notes'],
                                 'first_verdict_reason': r['reason'],
                                 'page_text_source': src or 'none found'}, ensure_ascii=False))
            L.append('PAGE TEXT for R#%02d:\n%s\n' % (i, txt or '(none)'))
        text = '\n'.join(L)
        if dry:
            print('batch of %d, prompt %d chars' % (len(batch), len(text)))
            continue
        env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
        r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL,
                             '--system-prompt', RECHECK_SYSTEM, '--json-schema', json.dumps(SCHEMA),
                             '--output-format', 'json', '--max-budget-usd', '2'],
                            input=text, capture_output=True, text=True, env=env, timeout=TIMEOUT)
        if r.returncode != 0:
            spend('recheck-prose', 0, 'failed')
            print('CALL FAILED, stopping:', (r.stdout + r.stderr)[-800:])
            return 1
        res = json.loads(r.stdout)
        body = res.get('structured_output') or res.get('result')
        body = json.loads(body) if isinstance(body, str) else body
        cost = float(res.get('total_cost_usd') or 0)
        total += cost
        keys = {'R#%02d' % i for i in range(len(batch))}
        got = collections.Counter(e.get('entry_key') for e in body.get('entries', []))
        bad = [] if set(got) == keys and max(got.values()) == 1 else ['keys %s' % dict(got)]
        for e in body.get('entries', []):
            d = (e.get('dataset') or '').strip()
            if e.get('verdict') not in MODEL_VERDICTS or (d and d not in existing) or \
                    (e.get('verdict') == 'repeat' and not d) or not (e.get('reason') or '').strip():
                bad.append('%s %r %r' % (e.get('entry_key'), e.get('verdict'), d))
        spend('recheck-prose', cost, 'ok' if not bad else 'failed')
        if bad:
            print('VALIDATION FAILED ($%.4f), stopping:' % cost, bad)
            return 1
        by = {e['entry_key']: e for e in body['entries']}
        for i, row in enumerate(batch):
            e = by['R#%02d' % i]
            if e['verdict'] != 'prose':
                print('  %s p%s %s: prose -> %s %s' % (row['edition'], row['pages'], row['name'][:60],
                                                      e['verdict'], e.get('dataset') or ''))
            row.update(verdict=e['verdict'], dataset=(e.get('dataset') or '').strip(),
                       reason=e['reason'].strip(), decided_on=today(),
                       decided_by='claude -p %s, re-check of prose with page text (rule 13c)' % MODEL)
        write_out(rows)
        print('batch of %d: $%.4f' % (len(batch), cost))
    print('re-check total $%.4f' % total)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edition', action='append')
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--recheck-prose', type=int, metavar='RUNS',
                    help='re-sort prose entries that mention counts/figures, with page text, in at most RUNS (<=3) calls')
    ap.add_argument('--consistency', action='store_true',
                    help='deterministic pass: same table, different verdicts across years')
    ap.add_argument('--prune', action='store_true',
                    help='delete rows whose entry is no longer on an unread page; no calls')
    ap.add_argument('--max-runs', type=int, default=15)
    a = ap.parse_args()
    if a.check:
        return check()
    if a.recheck_prose:
        return recheck_prose(a.recheck_prose, a.dry_run)
    if a.consistency:
        return consistency(not a.dry_run)
    if a.prune:
        un, _, _ = unread()
        want = {(B.base_edition(r['edition']), r['name'], r['pages']) for ed in un for r in un[ed]}
        rows = read_out()
        keep = [r for r in rows if (r['edition'], r['name'], r['pages']) in want]
        for r in rows:
            if r not in keep:
                print('pruned %s p%s %s (%s)' % (r['edition'], r['pages'], r['name'], r['verdict']))
        write_out(keep)
        print('%d rows -> %d' % (len(rows), len(keep)))
        return 0

    un, onread, ds = unread()
    existing = existing_datasets()
    rows = read_out()
    done = {r['edition'] for r in rows}
    eds = sorted(un, key=lambda e: int(e[2:]))
    if a.edition:
        eds = [e for e in eds if e in a.edition]
    total, runs = 0.0, 0
    print('%d unread entries across %d editions' % (sum(len(un[e]) for e in eds), len(eds)))
    for ed in eds:
        if ed in done and not a.redo:
            print('%s already written, skipped' % ed)
            continue
        listy = [r for r in un[ed] if deferred(r)]
        ask = [r for r in un[ed] if not deferred(r)]
        text = prompt(ed, ask, onread[ed], ds)
        if a.dry_run:
            print('%s: %d to sort, %d deferred (%s); prompt %d chars'
                  % (ed, len(ask), len(listy), '; '.join(r['name'][:40] for r in listy), len(text)))
            continue
        if runs >= a.max_runs:
            print('stopping at --max-runs %d' % a.max_runs)
            break
        out = [dict(edition=ed, name=r['name'], pages=r['pages'], verdict=DEFERRED, dataset='',
                    reason='a list of people; step 3, the list survey, reads these',
                    decided_by='rule: sort_catalogue.LIST_GRAIN/LIST_NAME', decided_on=today())
               for r in listy]
        if ask:
            runs += 1
            try:
                body, cost = call(text)
            except Exception as e:  # noqa: BLE001
                spend(ed, 0, 'failed')
                print('%s: CALL FAILED, stopping: %s' % (ed, e))
                return 1
            total += cost
            bad = validate(ed, ask, body, existing)
            spend(ed, cost, 'ok' if not bad else 'failed')
            if bad:
                dump = os.path.join(ROOT, 'build', 'sort-catalogue-%s.json' % ed)
                os.makedirs(os.path.dirname(dump), exist_ok=True)
                json.dump(body, open(dump, 'w'), indent=1)
                print('%s: VALIDATION FAILED ($%.4f), stopping; body in %s' % (ed, cost, dump))
                for b in bad:
                    print('  ', b)
                return 1
            by = {e['entry_key']: e for e in body['entries']}
            for i, r in enumerate(ask):
                e = by[key(ed, i)]
                out.append(dict(edition=ed, name=r['name'], pages=r['pages'], verdict=e['verdict'],
                                dataset=(e.get('dataset') or '').strip(), reason=e['reason'].strip(),
                                decided_by='claude -p %s, from the catalogue description' % MODEL,
                                decided_on=today()))
        else:
            cost = 0.0
        rows = [r for r in read_out() if r['edition'] != ed] + out
        write_out(rows)
        c = collections.Counter(r['verdict'] for r in out)
        print('%s: %d rows, $%.4f  %s' % (ed, len(out), cost, dict(c)))
    print('runs %d, total $%.4f' % (runs, total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
