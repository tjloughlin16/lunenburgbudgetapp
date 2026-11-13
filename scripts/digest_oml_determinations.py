#!/usr/bin/env python3
"""THE ATTORNEY GENERAL'S OPEN MEETING LAW DETERMINATIONS, DIGESTED ONCE PER LETTER.

    python3 scripts/digest_oml_determinations.py --limit 10          # next 10, newest first (paid)
    python3 scripts/digest_oml_determinations.py --limit 10 --dry-run   # what would run, no call
    python3 scripts/digest_oml_determinations.py --id oml-det-2026-98   # one letter (paid)
    python3 scripts/digest_oml_determinations.py --status            # held / digested / left
    python3 scripts/digest_oml_determinations.py --check             # every digest still holds

Section 2 of notes/handoffs-done/HANDOFF-OML-INDEX.md. TJ, 8 October 2026: "We'll build a
process identical to meeting minutes processing to do the determinations. But later." And,
12 November 2026, on starting it: "yes but try it in batches to confirm".

WHAT IS FREE AND WHAT IS PAID. The determination number, the letter's date, the public body
and the portal's own Violation field come from the catalogue row (sources/state-law/index.csv)
and the determinations each letter CITES come from a regex over its text -- no model. The
model (haiku, `claude -p --json-schema`, no tools) reads the letter once and returns the body
TYPE, each allegation the AG addressed with its issue, the AG's holding and the key passage,
and any remedy ordered.

EVERY QUOTE IS CHECKED VERBATIM against the letter's text (whitespace, quote marks and dashes
normalised -- a PDF breaks lines and curls quotes, a model does not). An allegation whose
passage is not verbatim keeps its issue and holding but loses the passage, and is counted in
`unquoted`; the model's word is never stored as the AG's. A holding is the AG's reading of the
law in THAT case; nothing here says what any Lunenburg board did.

READS ONLY the extracted text in sources/state-law/text/. It never OCRs or re-renders a letter
(TJ, 8 October 2026). Resumable: a letter with a digest is skipped. Honours build/STOP-METERED,
and stops before starting a letter once the weekly bar reaches --week-cap.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import claude_lean  # noqa: E402

ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, 'sources', 'state-law', 'index.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'oml-determinations')
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
STOP = os.path.join(ROOT, 'build', 'STOP-METERED')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = 'haiku'
STREAM = 'oml-digest'
TIMEOUT = 600
VERSION = 1

ISSUES = [
    'notice timing', 'notice content / topic specificity', 'acronyms and jargon',
    'discussion beyond the notice', 'votes and roll calls',
    'executive session: purpose', 'executive session: procedure',
    'executive session minutes', 'open session minutes', 'release of minutes',
    'remote participation', 'public access and recording', 'public comment',
    'deliberation outside a meeting', 'quorum / serial communication',
    'complaint procedure', 'jurisdiction / not a public body', 'other',
]
HOLDINGS = ['violation', 'no violation', 'not reached', 'declined to review']
BODY_TYPES = [
    'select board / board of selectmen', 'city council / town council', 'school committee',
    'regional school committee', 'finance / advisory committee', 'planning board',
    'zoning board of appeals', 'conservation commission', 'board of health',
    'housing authority', 'library trustees', 'state or regional body', 'other municipal body',
]

SYSTEM = """You read one Open Meeting Law determination letter from the Massachusetts Attorney \
General's Division of Open Government and return a structured digest of it.

Rules:
- One entry in `allegations` per distinct allegation the letter addresses or declines to address.
- `issue` is the closest category from the list. `holding` is what the AG decided on THAT \
allegation: violation, no violation, not reached (e.g. moot or untimely), or declined to review.
- `key_passage` is ONE sentence or clause copied EXACTLY, character for character, from the \
letter, that states the AG's reasoning or finding on that allegation. Copy, never paraphrase. \
At least 40 characters. Do not include footnote numbers.
- `summary` is one plain sentence (under 160 characters) saying what was alleged.
- `remedy`: if the AG ordered anything (e.g. immediate and future compliance, training, \
release of minutes, nullification), list each order; otherwise empty. `remedy_passage` is the \
sentence of the order copied exactly, or empty.
- Do not name private individuals (complainants, members of the public) in your own words."""


def schema():
    return {
        'type': 'object', 'additionalProperties': False,
        'required': ['body_type', 'allegations', 'remedy', 'remedy_passage', 'overall'],
        'properties': {
            'body_type': {'type': 'string', 'enum': BODY_TYPES},
            'overall': {'type': 'string', 'description': 'one sentence: what the letter decided'},
            'allegations': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False,
                'required': ['issue', 'summary', 'holding', 'key_passage'],
                'properties': {
                    'issue': {'type': 'string', 'enum': ISSUES},
                    'summary': {'type': 'string'},
                    'holding': {'type': 'string', 'enum': HOLDINGS},
                    'key_passage': {'type': 'string'},
                }}},
            'remedy': {'type': 'array', 'items': {'type': 'string'}},
            'remedy_passage': {'type': 'string'},
        }}


# ---- the catalogue -------------------------------------------------------------------------

LABEL = re.compile(r'AG determination (OML \d{4}-\d+), (\d{1,2})/(\d{1,2})/(\d{4}), (.*?) '
                   r'\(portal Violation field: ([^)]*)\)')


def letters():
    """Every held determination, newest first (by year, then number)."""
    out = []
    for r in csv.DictReader(open(INDEX, newline='')):
        if '/determinations/' not in r['local']:
            continue
        m = LABEL.match(r['label'])
        num = r['id'].split('-')
        out.append({
            'id': r['id'], 'year': int(num[2]), 'n': int(re.sub(r'\D.*', '', num[3]) or 0),
            'number': m.group(1) if m else '',
            'date': '%s-%02d-%02d' % (m.group(4), int(m.group(2)), int(m.group(3))) if m else '',
            'public_body': m.group(5) if m else '',
            'portal_violation': m.group(6) if m else '',
            'text': os.path.join(ROOT, r['text']), 'sha256': r['sha256'],
            'publisher_filename': r['publisher_filename'], 'local': r['local'],
        })
    out.sort(key=lambda d: (d['year'], d['n'], d['id']), reverse=True)
    return out


def out_path(d):
    return os.path.join(OUT, str(d['year']), d['id'] + '.json')


# ---- verbatim ------------------------------------------------------------------------------

_TR = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"',
                     '–': '-', '—': '-', ' ': ' ', '­': ''})


def squash(s):
    s = re.sub(r'===PAGE \d+===', ' ', s or '').translate(_TR)
    s = re.sub(r'-\s*\n\s*', '-', s)
    return re.sub(r'\s+', ' ', s).strip()


def verbatim(quote, body_sq):
    q = squash(quote)
    return len(q) >= 30 and q in body_sq


CITE = re.compile(r'OML\s+(\d{4})\s*[-–—]\s*(\d+)')


def citations(text, own):
    seen = []
    for y, n in CITE.findall(text):
        c = 'OML %s-%d' % (y, int(n))
        if c != own and c not in seen:
            seen.append(c)
    return seen


# ---- the paid call -------------------------------------------------------------------------

def log_spend(d, cost, result):
    new = not os.path.exists(SPEND)
    with open(SPEND, 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['at', 'stream', 'board', 'date', 'cost_usd', 'result'])
        if new:
            w.writeheader()
        w.writerow({'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'stream': STREAM,
                    'board': d['id'], 'date': d['date'], 'cost_usd': '%.4f' % (cost or 0),
                    'result': result})


def digest(d):
    text = open(d['text'], encoding='utf-8', errors='replace').read()
    prompt = ('Determination %s, dated %s, public body: %s.\n\nTHE LETTER:\n\n%s'
              % (d['number'], d['date'], d['public_body'], text))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    # The CLI replaces its own binary when it updates, so for a few seconds `claude` is not
    # there (12 November 2026: six letters went through, then three in a row failed with
    # ENOENT). Absolute path, and one retry after the update has had time to finish.
    exe = os.path.join(NODE22, 'claude')
    # Mid-update the binary is either missing (ENOENT) or half-written (ENOEXEC, seen at
    # 18:11 the same evening), so any OSError on launch waits and retries.
    for attempt in (1, 2, 3, 4):
        try:
            r = claude_lean.run([exe if os.path.exists(exe) else 'claude', '-p', '--tools', '',
                                 '--model', MODEL, '--system-prompt', SYSTEM,
                                 '--json-schema', json.dumps(schema()), '--output-format', 'json',
                                 '--max-budget-usd', '0.5'],
                                input=prompt, capture_output=True, text=True, env=env, timeout=TIMEOUT)
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(60)
    if r.returncode != 0:
        log_spend(d, 0, 'failed')
        raise RuntimeError('claude failed: ' + (r.stdout + r.stderr)[-600:])
    res = json.loads(r.stdout)
    cost = res.get('total_cost_usd') or 0
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or 'allegations' not in body:
        log_spend(d, cost, 'no structured output')
        raise RuntimeError('no structured output')
    log_spend(d, cost, 'ok')

    sq = squash(text)
    allegations, unquoted = [], 0
    for a in body['allegations']:
        ok = verbatim(a.get('key_passage', ''), sq)
        if not ok:
            unquoted += 1
        allegations.append({'issue': a['issue'], 'summary': a['summary'], 'holding': a['holding'],
                            'key_passage': a['key_passage'] if ok else ''})
    rp = body.get('remedy_passage', '')
    doc = {
        'id': d['id'], 'number': d['number'], 'date': d['date'], 'public_body': d['public_body'],
        'portal_violation': d['portal_violation'], 'body_type': body['body_type'],
        'overall': body.get('overall', ''),
        'allegations': allegations, 'unquoted': unquoted,
        'remedy': body.get('remedy') or [],
        'remedy_passage': rp if rp and verbatim(rp, sq) else '',
        'cites': citations(text, d['number']),
        'source': {'publisher_filename': d['publisher_filename'], 'local': d['local'],
                   'text': os.path.relpath(d['text'], ROOT), 'sha256': d['sha256']},
        'written': {'by': 'scripts/digest_oml_determinations.py', 'version': VERSION, 'model': MODEL,
                    'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'cost_usd': cost},
        'note': ('Read by a language model from the letter; every key passage is checked verbatim '
                 'against it and dropped if not. A holding is the Attorney General’s reading of '
                 'the law in this case only.'),
    }
    p = out_path(d)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    os.replace(tmp, p)
    return doc


# ---- the weekly guard ----------------------------------------------------------------------

def week_pct():
    try:
        import usage_governor as G
        G.fetch()
        h = G.readings()
        if h and time.time() - h[-1]['t'] < G.STALE_S:
            return h[-1]['u7']
    except Exception:
        pass
    return None


# ---- the commands --------------------------------------------------------------------------

def check():
    bad = n = 0
    for d in letters():
        p = out_path(d)
        if not os.path.exists(p):
            continue
        n += 1
        doc = json.load(open(p, encoding='utf-8'))
        sq = squash(open(d['text'], encoding='utf-8', errors='replace').read())
        if doc['source']['sha256'] != d['sha256']:
            print('STALE %s: letter sha256 changed' % d['id']); bad += 1
        for a in doc['allegations']:
            if a['key_passage'] and not verbatim(a['key_passage'], sq):
                print('NOT VERBATIM %s: %s' % (d['id'], a['key_passage'][:80])); bad += 1
            if a['issue'] not in ISSUES or a['holding'] not in HOLDINGS:
                print('BAD ENUM %s' % d['id']); bad += 1
    print('%d digest(s) checked, %d problem(s)' % (n, bad))
    return 1 if bad else 0


def status():
    ls = letters()
    done = [d for d in ls if os.path.exists(out_path(d))]
    print('%d letters held, %d digested, %d left' % (len(ls), len(done), len(ls) - len(done)))
    costs, agree, differ, alls, unq = [], 0, [], 0, 0
    for d in done:
        doc = json.load(open(out_path(d), encoding='utf-8'))
        c = doc['written'].get('cost_usd')
        if c:
            costs.append(c)
        alls += len(doc['allegations'])
        unq += doc['unquoted']
        # The portal's own Violation field is never put in the prompt, so it is an
        # independent check on the holdings -- of the letter as a whole, not each allegation.
        pv = (doc['portal_violation'] or '').strip().upper()
        if pv in ('YES', 'NO'):
            ours = any(a['holding'] == 'violation' for a in doc['allegations'])
            if ours == (pv == 'YES'):
                agree += 1
            else:
                differ.append(doc['number'])
    if done:
        print('portal Violation field agrees on %d of %d; differs: %s'
              % (agree, agree + len(differ), ', '.join(differ) or 'none'))
        print('allegations: %d, key passage not verbatim (dropped): %d' % (alls, unq))
    if costs:
        m = sum(costs) / len(costs)
        print('measured: $%.4f a letter over %d; the rest at that rate: $%.2f'
              % (m, len(costs), m * (len(ls) - len(done))))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--limit', type=int, default=0, help='digest at most N letters this run')
    ap.add_argument('--id', help='one letter by catalogue id (oml-det-YYYY-N)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--week-cap', type=float, default=90.0,
                    help='start no letter once the weekly bar is at or above this percent')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.status:
        return status()
    ls = letters()
    queue = [d for d in ls if d['id'] == a.id] if a.id else [d for d in ls if not os.path.exists(out_path(d))]
    if a.limit:
        queue = queue[:a.limit]
    if not queue:
        print('nothing to digest'); return 0
    print('%d letter(s), newest first: %s .. %s' % (len(queue), queue[0]['number'], queue[-1]['number']))
    if a.dry_run:
        for d in queue[:20]:
            print('  %s  %s  %s' % (d['number'], d['date'], d['public_body']))
        return 0
    total = fails = 0.0
    done = 0
    for i, d in enumerate(queue, 1):
        if os.path.exists(STOP):
            print('build/STOP-METERED present; stopping'); break
        if i == 1 or i % 10 == 0:
            u7 = week_pct()
            if u7 is not None and u7 >= a.week_cap:
                print('weekly bar %.0f%% >= cap %.0f%%; stopping' % (u7, a.week_cap)); break
        try:
            doc = digest(d)
        except Exception as e:  # noqa: BLE001
            fails += 1
            print('[%d/%d] %s FAILED: %s' % (i, len(queue), d['number'], str(e)[:300]))
            if fails >= 3:
                print('three failures; stopping'); break
            continue
        c = doc['written']['cost_usd'] or 0
        total += c
        done += 1
        print('[%d/%d] %s %s: %s, %d allegation(s), %d unquoted, %d cited ($%.4f)'
              % (i, len(queue), doc['number'], doc['public_body'], doc['body_type'],
                 len(doc['allegations']), doc['unquoted'], len(doc['cites']), c))
    if done:
        print('done: %d letter(s), $%.4f, $%.4f a letter' % (done, total, total / done))
    return 0


if __name__ == '__main__':
    sys.exit(main())
