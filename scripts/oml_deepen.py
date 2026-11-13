#!/usr/bin/env python3
"""OML REVIEW, SECOND PASS: an agent researches only the points the one-call review flagged.

    python3 scripts/oml_deepen.py school-committee 2026-09-16             # research flagged points
    python3 scripts/oml_deepen.py school-committee 2026-09-16 --dry-run   # list them, no call
    python3 scripts/oml_deepen.py --rate                                  # escalation rate, all reviews

TJ, 13 November 2026: the one call "needs to flag if an agentic review should be kicked off
for it, and if so, it can be" -- "and if that's a high percentage... then it means we need an
agentic loop to begin". So oml_review.py marks each point `escalate.needed`, with a reason and
one question; this script answers that question, and `--rate` reports how often it is asked.

WHAT MAKES IT AN AGENT. The one-call review cannot look anything up. Here Claude has READ-ONLY
tools (Read, Grep, Glob) over the 2,909 AG determination letters, their digests, every posted
agenda and minutes, and the captions -- and decides for itself what to open. Nothing else: no
shell, no writing, no web.

WHAT IT RETURNS, AND WHAT IS CHECKED. An outcome (confirmed / downgraded / upgraded /
unresolved), the point's status after research, and quotes. Every quote is checked VERBATIM by
this script, as oml_review.py checks its own: an AG letter quote against the law index, a
document quote against the file it names, a caption quote re-anchored to its second. Any quote
that fails and the research is discarded whole, and the point keeps its first-pass status. At
most MAX_POINTS per meeting; a hard dollar cap per point.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import claude_lean  # noqa: E402
import oml_law as L  # noqa: E402
import oml_review as R  # noqa: E402

ROOT = R.ROOT
MODEL = os.environ.get('OML_DEEPEN_MODEL', 'sonnet')
MAX_POINTS = 3
BUDGET_PER_POINT = '1.50'
TIMEOUT = 900
OUTCOMES = ['confirmed', 'downgraded', 'upgraded', 'unresolved']
DIRS = {
    'AG determination letters (text), one file per letter, named oml-det-YYYY-N.txt':
        os.path.join(ROOT, 'sources', 'state-law', 'text'),
    'AG determination digests (JSON: issue, holding, key passage per allegation)':
        os.path.join(ROOT, 'sources', 'data', 'oml-determinations'),
    'every posted agenda and minutes, as text, by board':
        os.path.join(ROOT, 'sources', 'meetings', 'text'),
    'machine captions of recordings (JSON segments with start seconds), by board':
        os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts'),
}

SYSTEM = '''You research ONE point raised by a first-pass Open Meeting Law review of a Massachusetts town board meeting. The first pass read only this meeting's agenda, minutes and captions and a small pack of AG rulings; it flagged this point because research could change it. Answer the QUESTION using your read-only tools, then stop.

How to research: Grep the AG determination letters for the specific facts (e.g. "roll call" "remote", "not listed on the notice" "vote"), read the strongest few, and prefer letters whose facts match this meeting and whose holding is on this issue. Check the meeting's own documents and other meetings of the same board (a later meeting's minutes may approve or correct these; an earlier agenda may show the topic). Captions are machine speech recognition: a finding aid.

Return:
- outcome: "confirmed" (the research supports the first-pass point as stated), "downgraded" (it weakens it -- e.g. the AG has held such facts acceptable, or another document answers it), "upgraded" (it strengthens it), "unresolved" (the research could not settle it).
- status: the point's status after research, one of the three.
- summary: at most two short sentences, plain English, saying what the research found. NEVER the words "violation", "violated", "illegal" or "unlawful".
- precedent: up to three AG letters, each with its id (oml-det-YYYY-N) and a CONTIGUOUS verbatim quote of 30-400 characters from that letter's text file.
- evidence: up to three quotes from meeting documents or captions, each with the ABSOLUTE path of the file you read it from and a CONTIGUOUS verbatim quote of 20-300 characters; for a captions file also `t`, the start second of the segment.
- note: one line on what you searched.
A ruling is how the AG read the law for another body on its facts; never present it as a finding about this board. Quote exactly; a quote that is not verbatim discards your whole answer.'''


def schema():
    return {
        'type': 'object', 'additionalProperties': False,
        'required': ['outcome', 'status', 'summary', 'precedent', 'evidence', 'note'],
        'properties': {
            'outcome': {'type': 'string', 'enum': OUTCOMES},
            'status': {'type': 'string', 'enum': R.STATUSES},
            'summary': {'type': 'string'},
            'precedent': {'type': 'array', 'maxItems': 3, 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['id', 'quote'],
                'properties': {'id': {'type': 'string'}, 'quote': {'type': 'string'}}}},
            'evidence': {'type': 'array', 'maxItems': 3, 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['path', 'quote'],
                'properties': {'path': {'type': 'string'}, 'quote': {'type': 'string'},
                               't': {'type': 'integer'}}}},
            'note': {'type': 'string'},
        }}


def review_path(board, date):
    hits = sorted(glob.glob(os.path.join(R.OUT, board, '%s-*.json' % date)))
    if not hits:
        raise SystemExit('no review of %s %s under %s; run oml_review.py first' % (board, date, R.rel(R.OUT)))
    return hits[0]


def prompt_for(doc, f):
    ev = '\n'.join('  - %s: "%s"' % (e['source'], e['quote']) for e in f['evidence'])
    prec = '\n'.join('  - %s: "%s"' % (p.get('number') or p['id'], p['quote']) for p in f.get('precedent') or [])
    where = '\n'.join('- %s: %s' % (k, v) for k, v in DIRS.items())
    files = '\n'.join('- %s: %s' % (k, os.path.join(ROOT, v['path'])) for k, v in doc['inputs'].items()
                      if k in ('agenda_text', 'minutes_text', 'transcript'))
    return ('MEETING: %s, %s.\n\nTHE POINT (first pass):\n  title: %s\n  issue: %s\n  status: %s\n'
            '  summary: %s\n  rule: %s "%s"\n  evidence:\n%s\n  precedent cited:\n%s\n\n'
            'WHY IT WAS FLAGGED: %s\nQUESTION: %s\n\nTHIS MEETING\'S FILES:\n%s\n\nWHERE YOU MAY SEARCH:\n%s\n'
            % (doc['board'], doc['date'], f['title'], f.get('issue', ''), f['status'], f['summary'],
               f['rule']['section'], f['rule']['quote'], ev, prec or '  (none)',
               f['escalate']['reason'], f['escalate']['question'], files, where))


def verify(ans, law_docs):
    """(answer, None) with quotes checked and enriched, or (None, why)."""
    if R.BANNED.search(ans['summary']):
        return None, 'used a word reserved for the Attorney General'
    for p in ans['precedent']:
        if not re.fullmatch(r'oml-det-\d{4}-\d+', p['id']) or not L.verbatim(p['quote'], [p['id']], law_docs):
            return None, 'precedent quote not verbatim in %s' % p['id']
        d = next(x for x in law_docs if x['id'] == p['id'])
        p.update({'label': d['label'], 'upstream': d['upstream'], 'our_copy': d['our_copy']})
        p.update(R.precedent_holding(p['id'], p['quote']))
    roots = [os.path.realpath(v) for v in DIRS.values()]
    for e in ans['evidence']:
        path = os.path.realpath(e['path'])
        if not any(path.startswith(r + os.sep) for r in roots) or not os.path.exists(path):
            return None, 'evidence path outside the searchable sources: %s' % e['path']
        if path.endswith('.json') and 'youtube-transcripts' in path:
            t = R.anchor(e['quote'], json.load(open(path))['segments'])
            if t is None:
                return None, 'caption quote not verbatim in %s' % R.rel(path)
            e['t'] = t
        elif not R.in_text(e['quote'], open(path, encoding='utf-8', errors='replace').read()):
            return None, 'quote not verbatim in %s' % R.rel(path)
        e['path'] = R.rel(path)
        e['url'] = evidence_url(e)
    return ans, None


def evidence_url(e):
    """Where a reader checks a quote: the video at its second, or the document's text on the site."""
    m = re.search(r'youtube-transcripts/[^/]+/\d{4}-\d{2}-\d{2}-([A-Za-z0-9_-]+)\.json$', e['path'])
    if m:
        return 'https://www.youtube.com/watch?v=%s&t=%ds' % (m.group(1), e.get('t') or 0)
    m = re.match(r'sources/meetings/text/(.+)$', e['path'])
    if m:
        return R.SITE + '/docs/minutes/text/' + m.group(1)
    m = re.match(r'sources/state-law/text/(oml-det-[\d-]+)\.txt$', e['path'])
    return R.SITE + '/docs/state-law/text/' + m.group(1) + '.txt' if m else ''


def deepen(board, date, dry=False):
    path = review_path(board, date)
    doc = json.load(open(path, encoding='utf-8'))
    todo = [i for i, f in enumerate(doc['findings'])
            if (f.get('escalate') or {}).get('needed') and 'deepened' not in f]
    print('%s %s: %d of %d point(s) flagged; researching %d'
          % (board, date, len(todo), len(doc['findings']), min(len(todo), MAX_POINTS)))
    if dry:
        for i in todo:
            f = doc['findings'][i]
            print('  - [%s] %s\n      Q: %s' % (f['escalate']['reason'], f['title'], f['escalate']['question']))
        return 0
    law_docs = L.documents()
    env = dict(os.environ, PATH=R.NODE22 + os.pathsep + os.environ.get('PATH', ''))
    for i in todo[:MAX_POINTS]:
        f = doc['findings'][i]
        r = claude_lean.run(['claude', '-p', '--model', MODEL, '--tools', 'Read,Grep,Glob',
                             '--allowedTools', 'Read,Grep,Glob', '--system-prompt', SYSTEM,
                             '--json-schema', json.dumps(schema()), '--output-format', 'json',
                             '--max-budget-usd', BUDGET_PER_POINT],
                            add_dirs=list(DIRS.values()), input=prompt_for(doc, f),
                            capture_output=True, text=True, env=env, timeout=TIMEOUT)
        stamp = {'by': 'scripts/oml_deepen.py', 'model': MODEL,
                 'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'reason': f['escalate']['reason'], 'question': f['escalate']['question'],
                 'status_before': f['status']}
        try:
            res = json.loads(r.stdout)
        except ValueError:
            res = {}
        cost = res.get('total_cost_usd') or 0
        R.log_spend(board, date, cost, 'deepen ok' if r.returncode == 0 else 'deepen failed')
        body = res.get('structured_output') or res.get('result')
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                body = None
        stamp['cost_usd'] = cost
        if r.returncode != 0 or not isinstance(body, dict):
            f['deepened'] = dict(stamp, outcome='failed', why=(r.stdout + r.stderr)[-300:])
            print('  ! %s: failed ($%.2f)' % (f['title'], cost))
            continue
        ans, why = verify(body, law_docs)
        if not ans:
            f['deepened'] = dict(stamp, outcome='discarded', why=why)
            print('  x %s: discarded, %s ($%.2f)' % (f['title'], why, cost))
            continue
        f['deepened'] = dict(stamp, **ans)
        if ans['outcome'] != 'unresolved':
            f['status'] = ans['status']
        print('  %s %s: %s -> %s ($%.2f)' % ('✓', f['title'], stamp['status_before'], f['status'], cost))
    doc['standout'], doc['standout_scores'] = R.standout(doc['findings'])
    doc['counts'] = {s: sum(1 for f in doc['findings'] if f['status'] == s) for s in R.STATUSES}
    R.write_json(path, doc)
    if not os.environ.get('OML_OUT'):
        R.write_json(R.pub_path(board, date, doc['video_id']), doc)
    return 0


def rate():
    flagged = total = reviews = 0
    by_reason = {}
    for p in sorted(glob.glob(os.path.join(R.OUT, '*', '*.json'))):
        doc = json.load(open(p, encoding='utf-8'))
        if 'escalation' not in doc:
            continue
        reviews += 1
        total += len(doc['findings'])
        for f in doc['findings']:
            e = f.get('escalate') or {}
            if e.get('needed'):
                flagged += 1
                by_reason[e['reason']] = by_reason.get(e['reason'], 0) + 1
    if not total:
        print('no review carries an escalation flag yet')
        return 0
    r = flagged / total
    print('escalation: %d of %d points (%.0f%%) across %d review(s); %s'
          % (flagged, total, 100 * r, reviews, ', '.join('%d %s' % (v, k) for k, v in sorted(by_reason.items()))))
    print('ABOVE the %.0f%% line: start the review agentic.' % (100 * R.ESCALATION_RATE_LINE) if r > R.ESCALATION_RATE_LINE
          else 'below the %.0f%% line: one call plus research on flagged points.' % (100 * R.ESCALATION_RATE_LINE))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--rate', action='store_true')
    a = ap.parse_args()
    if a.rate:
        return rate()
    if not (a.board and a.date):
        ap.error('board and date, or --rate')
    return deepen(a.board, a.date, a.dry_run)


if __name__ == '__main__':
    sys.exit(main())
