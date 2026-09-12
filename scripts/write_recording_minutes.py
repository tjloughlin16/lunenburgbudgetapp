#!/usr/bin/env python3
"""Minutes of a recorded meeting, written from our transcript, one file per recording.

    python3 scripts/write_recording_minutes.py school-committee 2026-07-29   # one meeting
    python3 scripts/write_recording_minutes.py --board school-committee --limit 5
    python3 scripts/write_recording_minutes.py --all                        # every transcript
    python3 scripts/write_recording_minutes.py --check                      # every file valid, linked, current
    python3 scripts/write_recording_minutes.py --status

WHY. 231 meetings in this town have no surviving record but the recording, 162 of them
School Committee. The captions make them searchable; they do not make them READABLE --
nobody sits through 4,000 caption lines to learn whether a transfer was voted. TJ, 11
September 2026: *"we need to process all the transcripts and create our own meeting
minutes based on them ... VOTES taken at the meeting (outside normal meeting votes like
adjournment), budget related items discussed, transfers, decisions made, topics
discussed with their resolutions."*

WHAT THESE ARE, AND ARE NOT. They are OUR minutes, written by a language model from OUR
machine captions of a video. Two derived layers stand between them and the meeting. So:

  * Every item carries the SECOND in the recording it came from, and the citation is the
    video at that second. Never this file. The reader is sent to the moment.
  * A figure is written AS HEARD and flagged. A caption model hears *fifteen hundred*,
    *$1,500* and *$50* alike. A figure here is a place to look, not a number to quote.
  * A name is written as heard and may be wrong; the model is told not to guess.
  * A vote's outcome is recorded only if the count or the result was audible; otherwise
    `outcome: "not audible"` -- which is a finding about the recording, not a guess.
  * Where the town published minutes for the same meeting, ours link to theirs and say so.
    Theirs are the record. Ours are the finding aid to the recording.

Rule 7 and rule 13 apply with full force, and the schema enforces the parts a schema can.

HOW IT IS WRITTEN. `claude -p` with no tools and a JSON schema, so the output is one
structured document that either validates or is refused. The transcript is sent as
timestamped lines grouped to ~20 seconds each, which is what makes the timestamps in the
answer honest: the model can only cite a time it was shown.

WHERE THEY LIVE. `sources/data/recording-minutes/<board>/<date>-<video_id>.json`, in git:
they are small, they are ours, and a reviewer needs to diff them. Each records the sha256
of the transcript it was written from, and `--check` fails if the transcript has since
changed or the file no longer parses.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts')
TRANSCRIPT_INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
MEETINGS_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
SITE = 'https://lunenburgbudgetproject.org'
MODEL = 'sonnet'
GROUP_SECONDS = 20

WARNING = ('OUR MINUTES OF A RECORDING, written by a language model from machine captions. '
           'Two derived layers stand between this file and the meeting. Cite the video at the '
           'timestamp, never this file. Figures are as heard and may be wrong; names may be '
           'wrong; where the town published minutes, those are the record.')

# A CONTROLLED LIST, so a tag means the same thing on every meeting and a reader can
# follow one across boards. Free text would give "sports", "athletics" and "the football
# program" for the same thing. Add to the list; do not let the model invent.
TAGS = [
    'budget', 'budget-fy26', 'budget-fy27', 'budget-fy28', 'state-aid', 'chapter-70',
    'override', 'town-meeting', 'warrant-article', 'transfers', 'free-cash', 'capital',
    'debt', 'tax-rate', 'grants', 'esser', 'fees', 'contracts-and-unions', 'hiring',
    'staffing', 'layoffs', 'special-education', 'out-of-district', 'enrollment',
    'school-choice', 'monty-tech', 'athletics', 'transportation', 'facilities',
    'turkey-hill', 'primary-school', 'middle-school', 'high-school', 'technology',
    'curriculum', 'policy', 'executive-session', 'public-comment', 'health-insurance',
    'retirement', 'town-departments', 'public-safety', 'roads-and-dpw', 'water-sewer',
    'planning-and-zoning', 'elections', 'legal', 'msba', 'recreation', 'library',
    'seniors', 'housing', 'economic-development', 'personnel', 'superintendent-report',
]

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['headline', 'summary', 'attendees', 'public_comment', 'tags', 'votes', 'budget_items',
                 'transfers', 'decisions', 'topics', 'not_audible', 'confidence'],
    'properties': {
        'attendees': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['name_as_heard', 'role'],
            'properties': {
                'name_as_heard': {'type': 'string', 'description': 'exactly as the captions render it; may be wrong'},
                'role': {'type': 'string', 'description': 'chair, member, superintendent, business manager, town manager, town accountant, student representative, presenter, or as stated'},
                'remote': {'type': 'boolean', 'description': 'true if said to be attending by Zoom or phone'},
            }},
            'description': 'board members and officials identified as present -- by roll call, by the chair, or by being addressed. Not the public.'},
        'public_comment': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['t', 'topic'],
            'properties': {
                't': {'type': 'integer'},
                'topic': {'type': 'string', 'description': 'what was raised, in a sentence'},
                'speaker_as_heard': {'type': 'string', 'description': 'ONLY if the speaker stated their own name for the record; exactly as heard; omit otherwise'},
                'stated_role': {'type': 'string', 'description': 'parent, resident, teacher, coach, booster president... only if they said so'},
            }},
            'description': 'each person who spoke during public comment or from the floor'},
        'tags': {'type': 'array', 'items': {'type': 'string', 'enum': TAGS},
                 'description': 'every topic from the controlled list that this meeting substantively touched'},
        'headline': {'type': 'string', 'description': 'THE ONE THING: the most consequential decision or discussion of the meeting, as one plain sentence under 120 characters, the most important part first. A vote outcome if there was a substantive one; otherwise what the meeting was really about. No figures from captions.'},
        'summary': {'type': 'string', 'description': 'Two or three sentences: what this meeting was mostly about and what, if anything, was decided. No figures.'},
        'votes': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['t', 'motion', 'outcome', 'procedural'],
            'properties': {
                't': {'type': 'integer', 'description': 'seconds into the recording where the motion is made'},
                'motion': {'type': 'string', 'description': 'what was moved, in one sentence, as heard'},
                'outcome': {'type': 'string', 'description': '"passed", "failed", a count like "passed 5-0", or "not audible"'},
                'procedural': {'type': 'boolean', 'description': 'true for adjournment, approving prior minutes, accepting the agenda, entering executive session'},
                'moved_by': {'type': 'string', 'description': 'name as heard, or omit'},
            }}},
        'budget_items': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['t', 'topic', 'what_was_said'],
            'properties': {
                't': {'type': 'integer'},
                'topic': {'type': 'string', 'description': 'the budget line, fund, grant, fee or cost being discussed'},
                'what_was_said': {'type': 'string', 'description': 'two sentences at most, paraphrased, no figures unless in figures_as_heard'},
                'figures_as_heard': {'type': 'array', 'items': {'type': 'string'}, 'description': 'each figure exactly as the captions render it, e.g. "fifteen hundred", "$1.2 million"'},
            }}},
        'transfers': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['t', 'description', 'outcome'],
            'properties': {
                't': {'type': 'integer'},
                'description': {'type': 'string', 'description': 'from what to what, as heard'},
                'amount_as_heard': {'type': 'string'},
                'outcome': {'type': 'string', 'description': 'voted / discussed only / not audible'},
            }}},
        'decisions': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['t', 'decision'],
            'properties': {
                't': {'type': 'integer'},
                'decision': {'type': 'string', 'description': 'something settled at this meeting that was not a formal vote, e.g. a direction to the superintendent, a date set, a request agreed'},
            }}},
        'topics': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['t_start', 't_end', 'topic', 'resolution', 'tags'],
            'properties': {
                't_start': {'type': 'integer'},
                't_end': {'type': 'integer'},
                'topic': {'type': 'string'},
                'resolution': {'type': 'string', 'description': 'how it ended: voted, tabled, referred, informational, no resolution'},
                # TIME BY SUBJECT. TJ, 12 September: "How much time does that committee talk
                # about X?" Each topic carries one to three tags from the controlled list, so
                # (t_end - t_start) can be summed by tag across a board's meetings.
                'tags': {'type': 'array', 'items': {'type': 'string', 'enum': TAGS}, 'minItems': 0, 'maxItems': 3,
                         'description': 'one to three tags from the controlled list for this topic; empty only for procedural stretches'},
            }}},
        'not_audible': {'type': 'array', 'items': {'type': 'string'},
                        'description': 'things the captions could not settle: a vote count, a figure, who spoke'},
        'confidence': {'type': 'string', 'enum': ['high', 'moderate', 'low'],
                       'description': 'how well the captions carried the meeting: low if long stretches are garbled or missing'},
    },
}

SYSTEM = """You write minutes of a public meeting from machine-generated captions of its video.

The captions are a speech model's rendering and are wrong in specific ways: numbers are unreliable (the model hears "fifteen hundred", "$1,500" and "$50" alike), names are mangled, and speakers are not identified. You will be given the captions as lines each prefixed with the time in seconds.

Rules, none optional:
1. Every item cites the second it came from, taken from the line prefixes. Never invent a time.
2. Write figures exactly as the captions render them, in figures_as_heard, and never restate a figure in prose as if it were established.
3. Write names as heard. If unsure, describe the role ("the superintendent", "a parent") instead.
4. A vote's outcome is "not audible" unless the result or the count is actually in the captions. Do not infer that a motion passed.
5. Votes: mark adjournment, approval of prior minutes, acceptance of the agenda and entering executive session as procedural: true. Everything else false.
6. budget_items is everything touching money: budget lines, grants, fees, transfers, contracts, costs, revenue, reserves, state aid, enrollment as it affects aid.
7. transfers are line-item or reserve transfers specifically, with the amount as heard.
8. decisions are things settled without a formal vote.
9. topics cover the whole meeting in order, with a start and end second and how each ended.
10. Do not summarise what the captions do not contain. If a stretch is garbled, say so in not_audible.
11. Public comment: record each speaker's topic; record the speaker's name ONLY if they stated it themselves for the record, and exactly as heard.
12. attendees: officials and members identified as present, with the role as stated or as evident from how they are addressed. Never the public.
13. tags (meeting-level): choose every tag from the controlled list that the meeting substantively touched; "turkey-hill" is Turkey Hill Elementary, "primary-school" is Lunenburg Primary School.
15. headline: the one most consequential thing, first and plainly, under 120 characters -- what a resident who reads nothing else should know.
14. topics[].tags: one to three tags from the same list for each topic, so time can be summed by subject. A procedural stretch (pledge, adjournment) gets none. "public-comment" means comment from the floor by residents only -- a public interview of a candidate is hiring; a board member speaking is not public comment.

Return only the JSON."""


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def transcripts():
    out = []
    for r in csv.DictReader(open(TRANSCRIPT_INDEX, encoding='utf-8', errors='replace')):
        p = os.path.join(ROOT, r['path'])
        if os.path.exists(p):
            out.append({'path': p, 'rel': r['path'], 'board_slug': r['board_slug'],
                        'date': r['meeting_date'], 'video_id': r['video_id']})
    return out


def town_documents():
    """{(board_slug, date): [{kind, url, path}]} -- what the town published for that meeting."""
    out = {}
    for r in csv.DictReader(open(MEETINGS_INDEX, encoding='utf-8', errors='replace')):
        stem = os.path.splitext(r['path'])[0]
        slug = stem.split('/')[0]
        out.setdefault((slug, r['date']), []).append({
            'kind': r['kind'], 'url': r['url'],
            'text_url': '%s/docs/minutes/text/%s.txt' % (SITE, stem),
            'path': 'sources/meetings/' + r['path'],
        })
    return out


def lines_for(doc):
    """The captions as `[t] text` lines, grouped to ~GROUP_SECONDS so the prompt is a
    fifth the length of the raw segments and every line still carries a citable time."""
    out, cur, cur_t = [], [], None
    for s in doc['segments']:
        t = int(float(s.get('start') or 0))
        if cur_t is None:
            cur_t = t
        if t - cur_t >= GROUP_SECONDS and cur:
            out.append('[%d] %s' % (cur_t, ' '.join(cur)))
            cur, cur_t = [], t
        cur.append((s.get('text') or '').replace('\n', ' ').strip())
    if cur:
        out.append('[%d] %s' % (cur_t, ' '.join(cur)))
    return out


def out_path(entry):
    return os.path.join(OUT, entry['board_slug'], '%s-%s.json' % (entry['date'], entry['video_id']))


def write_one(entry, docs, force=False):
    path = out_path(entry)
    sha = sha256_of(entry['path'])
    if os.path.exists(path) and not force:
        have = json.load(open(path))
        if have.get('source', {}).get('sha256') == sha:
            return 'current'
    doc = json.load(open(entry['path'], encoding='utf-8'))
    lines = lines_for(doc)
    if len(lines) < 5:
        return 'too short'
    board = (doc.get('title') or entry['board_slug'].replace('-', ' ').title())
    prompt = ('Meeting: %s, %s. Recording: %s\n\nCaptions (%d lines, [seconds] text):\n\n%s'
              % (board, entry['date'], doc.get('video_url'), len(lines), '\n'.join(lines)))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL,
                        '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA),
                        '--output-format', 'json', '--max-budget-usd', '2'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode != 0:
        raise SystemExit('claude failed on %s:\n%s' % (entry['rel'], (r.stdout + r.stderr)[-3000:]))
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if isinstance(body, dict) and 'tags' in body:
        body['tags'] = sorted(set(body['tags']))
    if not isinstance(body, dict) or 'votes' not in body:
        raise SystemExit('no structured output for %s: %s' % (entry['rel'], str(res)[:800]))
    video_url = doc.get('video_url') or 'https://www.youtube.com/watch?v=' + entry['video_id']
    segs = doc.get('segments') or []
    last = segs[-1] if segs else {}
    duration_s = int(float(last.get('start') or 0) + float(last.get('duration') or 0))
    spoken_chars = sum(len(x.get('text') or '') for x in segs)
    minutes = {
        'warning': WARNING,
        'board_slug': entry['board_slug'],
        'board': board,
        'meeting_date': entry['date'],
        'video_id': entry['video_id'],
        'video_url': video_url,
        'cite': 'the video at &t=<seconds>s; every t below is such a second',
        'source': {'transcript': entry['rel'], 'sha256': sha, 'caption_lines': len(lines),
                   'segments': len(segs)},
        # MEASURED, not asked: the recording's length from the last caption's end, and how
        # much was spoken. A meeting can be long and quiet.
        'recording': {'duration_s': duration_s, 'duration': '%d:%02d' % (duration_s // 3600, (duration_s % 3600) // 60),
                      'spoken_chars': spoken_chars, 'words_approx': spoken_chars // 6},
        'town_published': docs.get((entry['board_slug'], entry['date']), []),
        'written': {'by': 'scripts/write_recording_minutes.py', 'model': MODEL,
                    'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'cost_usd': res.get('total_cost_usd')},
        'minutes': body,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(minutes, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    digest(path)
    return 'written ($%.3f)' % (res.get('total_cost_usd') or 0)


HEADLINE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['headline'],
                   'properties': {'headline': {'type': 'string'}}}


def headline(path):
    """Add a headline to a minutes file written before the schema asked for one. One
    small call over the file's own summary, votes and decisions -- not the captions."""
    m = json.load(open(path, encoding='utf-8'))
    mm = m['minutes']
    if mm.get('headline'):
        return 'current'
    votes = [v for v in mm['votes'] if not v.get('procedural')]
    prompt = ('From these minutes of a %s meeting on %s, write the ONE most consequential thing as one '
              'plain sentence under 120 characters, most important part first, no figures. '
              'A substantive vote outcome if there was one; otherwise what the meeting was really about.\n\n'
              'Summary: %s\n\nVotes:\n%s\n\nDecisions:\n%s'
              % (m['board'], m['meeting_date'], mm['summary'],
                 '\n'.join('- %s — %s' % (v['motion'], v['outcome']) for v in votes) or '- none',
                 '\n'.join('- ' + d['decision'] for d in mm.get('decisions', [])) or '- none'))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL,
                        '--json-schema', json.dumps(HEADLINE_SCHEMA), '--output-format', 'json',
                        '--max-budget-usd', '0.3'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        raise SystemExit('claude failed on headline for %s' % path)
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    mm['headline'] = body['headline'].strip()
    m['written'].setdefault('backfilled', []).append({'field': 'headline', 'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'cost_usd': res.get('total_cost_usd')})
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(m, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return 'headlined ($%.3f): %s' % (res.get('total_cost_usd') or 0, mm['headline'][:80])


DIGEST_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['what_happened', 'why_it_matters', 'watch_next'],
    'properties': {
        'what_happened': {'type': 'array', 'minItems': 2, 'maxItems': 5, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['line', 't'],
            'properties': {'line': {'type': 'string', 'description': 'one plain sentence, under 160 characters, the most consequential first; no figures from captions'},
                           't': {'type': 'integer', 'description': 'the second in the recording it rests on, from the minutes'}}}},
        'why_it_matters': {'type': 'array', 'minItems': 1, 'maxItems': 3, 'items': {
            'type': 'string', 'description': 'one sentence for a resident: what this touches -- a bill, a school, a service, a vote they will be asked to take. Judgement, plainly, and never an accusation.'}},
        'watch_next': {'type': 'array', 'minItems': 0, 'maxItems': 2, 'items': {
            'type': 'string', 'description': 'what to watch for next -- a date, a vote, a document -- if the minutes give one'}},
    },
}

DIGEST_SYSTEM = """You write the short digest that sits above a set of meeting minutes on a public budget website, in the site's own voice: plain, exact, no first person, no adjectives of opinion.

You are given our minutes of a recorded meeting (written from machine captions). Write:
- what_happened: two to five sentences, the most consequential first, each carrying the second in the recording it rests on. Use the vote outcomes and decisions in the minutes. Never restate a figure from the captions as fact; say "a transfer" or "the amount as heard" rather than the number.
- why_it_matters: one to three sentences for a resident -- what this touches: a tax bill, a school, a program, a service, a vote they will be asked to take. This is judgement and it is allowed to be, but it names mechanisms, never motives, and never a person as the cause.
- watch_next: what to watch for next, only if the minutes give a date, a vote or a document.

Return only the JSON."""


def digest(path):
    """QUEUE 12a, the digest proper. A third pass over OUR minutes file -- not the
    captions -- so it costs cents. TJ: 'i personally was watching every meeting ... and
    taking notes, and posting them online. People loved it because i focused only on the
    details that mattered to them.' The site now does that, in the site's voice."""
    m = json.load(open(path, encoding='utf-8'))
    mm = m['minutes']
    if m.get('digest'):
        return 'current'
    votes = [v for v in mm['votes'] if not v.get('procedural')]
    prompt = ('%s, %s.\n\nHEADLINE: %s\nSUMMARY: %s\n\nVOTES:\n%s\n\nDECISIONS:\n%s\n\nBUDGET ITEMS:\n%s\n\nPUBLIC COMMENT:\n%s\n\nTOPICS:\n%s'
              % (m['board'], m['meeting_date'], mm.get('headline', ''), mm['summary'],
                 '\n'.join('- [t=%d] %s — %s' % (v['t'], v['motion'], v['outcome']) for v in votes) or '- none',
                 '\n'.join('- [t=%d] %s' % (d['t'], d['decision']) for d in mm.get('decisions', [])) or '- none',
                 '\n'.join('- [t=%d] %s: %s' % (b['t'], b['topic'], b['what_was_said']) for b in mm.get('budget_items', [])[:12]) or '- none',
                 '\n'.join('- [t=%d] %s' % (p['t'], p['topic']) for p in mm.get('public_comment', [])) or '- none',
                 '\n'.join('- [t=%d–%d] %s — %s' % (t['t_start'], t['t_end'], t['topic'], t['resolution']) for t in mm.get('topics', []))))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', DIGEST_SYSTEM,
                        '--json-schema', json.dumps(DIGEST_SCHEMA), '--output-format', 'json', '--max-budget-usd', '0.5'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        raise SystemExit('claude failed on digest for %s' % path)
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    # NO CAPTION FIGURE REACHES A DIGEST. The prompt says so and one slipped through on
    # the first run ("$418,000"); a rule enforced by asking is not a rule. Any dollar
    # amount or large bare number becomes "as heard" here, mechanically.
    import re as _re
    scrub = lambda x: _re.sub(r'\b(?:the |an? )?\$\s?[\d,]+(?:\.\d+)?\s?(?:million|thousand|k|M|K)?\b\s*', 'an amount as heard ', x).replace('  ', ' ').strip()
    for w in body['what_happened']:
        w['line'] = scrub(w['line'])
    body['why_it_matters'] = [scrub(x) for x in body['why_it_matters']]
    body['watch_next'] = [scrub(x) for x in body['watch_next']]
    # Every second cited must be one the minutes hold.
    known = {v['t'] for v in mm['votes']} | {d['t'] for d in mm.get('decisions', [])} | {b['t'] for b in mm.get('budget_items', [])} \
        | {p['t'] for p in mm.get('public_comment', [])} | {t['t_start'] for t in mm.get('topics', [])}
    for w in body['what_happened']:
        if w['t'] not in known:
            w['t'] = min(known, key=lambda k: abs(k - w['t'])) if known else 0
    m['digest'] = dict(body, written={'by': 'scripts/write_recording_minutes.py --digest', 'model': MODEL,
                                      'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                      'cost_usd': res.get('total_cost_usd')})
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(m, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return 'digested ($%.3f): %s' % (res.get('total_cost_usd') or 0, body['what_happened'][0]['line'][:80])


RETAG_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['topics'],
                'properties': {'topics': {'type': 'array', 'items': {
                    'type': 'object', 'additionalProperties': False, 'required': ['i', 'tags'],
                    'properties': {'i': {'type': 'integer'},
                                   'tags': {'type': 'array', 'items': {'type': 'string', 'enum': TAGS}, 'maxItems': 3}}}}}}


def retag(path):
    """Add topic tags to a minutes file written before topics carried them. One small
    model call over the topic titles alone -- a few cents, not another $0.50 read of the
    captions -- and the file's source hash is untouched because the captions were not."""
    m = json.load(open(path, encoding='utf-8'))
    topics = m['minutes'].get('topics', [])
    if not topics or all('tags' in t for t in topics):
        return 'current'
    prompt = ('Tag each topic with one to three tags from this list, or none for a procedural stretch. '
              '"public-comment" means comment FROM THE FLOOR by residents, and nothing else: a public '
              'interview of a candidate is hiring, a board member speaking is not public comment. '
              'Tags: %s\n\nTopics:\n%s' % (', '.join(TAGS),
              '\n'.join('%d. %s — %s' % (i, t['topic'], t['resolution']) for i, t in enumerate(topics))))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL,
                        '--json-schema', json.dumps(RETAG_SCHEMA), '--output-format', 'json',
                        '--max-budget-usd', '0.5'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        raise SystemExit('claude failed retagging %s' % path)
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    got = {x['i']: sorted(set(x['tags'])) for x in body['topics']}
    for i, t in enumerate(topics):
        t['tags'] = got.get(i, [])
    m['written']['retagged'] = {'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                'cost_usd': res.get('total_cost_usd')}
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(m, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return 'retagged ($%.3f)' % (res.get('total_cost_usd') or 0)


def check():
    docs = town_documents()
    by_rel = {t['rel']: t for t in transcripts()}
    bad = 0
    files = glob.glob(os.path.join(OUT, '*', '*.json'))
    for f in sorted(files):
        try:
            m = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            print('UNREADABLE %s: %s' % (os.path.relpath(f, ROOT), e)); bad += 1; continue
        src = m.get('source', {}).get('transcript')
        t = by_rel.get(src)
        if not t:
            print('ORPHAN %s: transcript %s is not in the index' % (os.path.relpath(f, ROOT), src)); bad += 1; continue
        if sha256_of(t['path']) != m['source']['sha256']:
            print('STALE %s: transcript changed since these minutes were written' % os.path.relpath(f, ROOT)); bad += 1
        mm = m.get('minutes', {})
        if not mm.get('headline'):
            print('NO HEADLINE %s: run --retag' % os.path.relpath(f, ROOT)); bad += 1
        if not m.get('digest'):
            print('NO DIGEST %s: run --retag' % os.path.relpath(f, ROOT)); bad += 1
        else:
            dg = m['digest']
            texts = [w['line'] for w in dg['what_happened']] + dg['why_it_matters'] + dg['watch_next']
            if any(re.search(r'\$\s?[\d,]', x) for x in texts):
                print('CAPTION FIGURE IN DIGEST %s' % os.path.relpath(f, ROOT)); bad += 1
        for t in mm.get('topics', []):
            if 'tags' not in t:
                print('NO TOPIC TAGS %s: run --retag' % os.path.relpath(f, ROOT)); bad += 1; break
        for k in ('votes', 'budget_items', 'transfers', 'decisions', 'topics'):
            for it in mm.get(k, []):
                tt = it.get('t', it.get('t_start'))
                if not isinstance(tt, int) or tt < 0:
                    print('NO TIME %s: %s item without a second' % (os.path.relpath(f, ROOT), k)); bad += 1
        if m.get('town_published') != docs.get((m['board_slug'], m['meeting_date']), []):
            print('LINKS %s: the town-published documents for this meeting have changed' % os.path.relpath(f, ROOT)); bad += 1
    print('%d minutes file(s) checked, %d problem(s)' % (len(files), bad))
    return 1 if bad else 0


def status():
    have = {os.path.relpath(f, OUT) for f in glob.glob(os.path.join(OUT, '*', '*.json'))}
    ts = transcripts()
    by_board = {}
    for t in ts:
        k = t['board_slug']
        by_board.setdefault(k, [0, 0])
        by_board[k][0] += 1
        if os.path.relpath(out_path(t), OUT) in have:
            by_board[k][1] += 1
    for k, (n, w) in sorted(by_board.items()):
        print('  %-40s %4d transcript(s), %4d with minutes' % (k, n, w))
    print('  %d of %d' % (sum(w for n, w in by_board.values()), len(ts)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--board')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--retag', action='store_true', help='add topic tags to minutes written before topics carried them')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.retag:
        for f in sorted(glob.glob(os.path.join(OUT, '*', '*.json'))):
            print('%s  %s' % (os.path.relpath(f, OUT), retag(f)), flush=True)
            print('%s  %s' % (os.path.relpath(f, OUT), headline(f)), flush=True)
            print('%s  %s' % (os.path.relpath(f, OUT), digest(f)), flush=True)
        return 0
    if a.status:
        status(); return 0
    docs = town_documents()
    ts = transcripts()
    if a.board and a.date:
        ts = [t for t in ts if t['board_slug'] == a.board and t['date'] == a.date]
    elif a.board:
        ts = [t for t in ts if t['board_slug'] == a.board]
    elif not a.all:
        ap.error('name a board and date, --board, or --all')
    ts.sort(key=lambda t: t['date'], reverse=True)
    if a.limit:
        ts = ts[:a.limit]
    if not ts:
        raise SystemExit('no transcript matches')
    for t in ts:
        print('%s %s  %s' % (t['board_slug'], t['date'], write_one(t, docs, force=a.force)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
