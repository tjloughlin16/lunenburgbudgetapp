#!/usr/bin/env python3
"""THE LEADING OML RULINGS, PER ISSUE: a model-free index over the AG's determinations.

    python3 scripts/build_oml_leading_rulings.py           # write sources/data/oml-leading-rulings.json
    python3 scripts/build_oml_leading_rulings.py --check   # fail if it no longer reproduces

WHAT IT READS. The 2,909 determination digests in sources/data/oml-determinations/ (written by
digest_oml_determinations.py: each allegation's issue, the AG's holding on it and a key passage
checked verbatim against the letter) and each letter's text in sources/state-law/text/.

WHAT "LEADING" MEANS HERE, and it is OURS: a ruling the AG's own later letters cite most often.
`cited_by` is the number of distinct determinations whose citation list names it. No model is
involved; the ranking is arithmetic over the citation lists, and the rule is written below so a
reader can rerun it.

PER ISSUE, at most PER_ISSUE rulings, picked in this order (each pick skips one already taken):
  1. the two most cited;
  2. the most cited against a school committee (regional included) -- the body this is built to
     review; ties go to the newer letter;
  3. the newest letter on the issue -- the law's current reading, and the only way a rule changed
     since 2012 (remote participation, chiefly) is represented;
  4. if the picks so far hold only one outcome, the most cited ruling with the other one, so the
     pack never shows only one side;
  5. then by citations until full.

ONLY RULINGS DECIDED ON THE MERITS (holding `violation` or `no violation`) with a key passage of
80-700 characters that is STILL verbatim in the letter's text. The passage is re-checked here, not trusted from
the digest.

A HOLDING IS AGAINST ONE BODY, IN ONE CASE. `public_body` and `body_type` say which; a
determination letter may hold against a different body than its title names (T-8C699's sample
found five). A ruling is how the AG read the law for that body on those facts, not a finding
about any Lunenburg board.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oml_law as L  # noqa: E402

ROOT = os.path.dirname(HERE)
DIGESTS = os.path.join(ROOT, 'sources', 'data', 'oml-determinations')
TEXTS = os.path.join(ROOT, 'sources', 'state-law', 'text')
OUT = os.path.join(ROOT, 'sources', 'data', 'oml-leading-rulings.json')

PER_ISSUE = 5
MAX_PASSAGE = 700
# A bare conclusion ("Therefore, we find no violation as to this allegation.") states an outcome
# and teaches nothing about the rule, so a passage must carry some reasoning to be picked.
MIN_PASSAGE = 80
SCHOOL = {'school committee', 'regional school committee'}
DECIDED = {'violation', 'no violation'}
# The issues a review of ONE meeting's published record can bear on. Left out: deliberation
# outside a meeting and serial communication (no record shows them -- oml_review.CANNOT_SEE),
# complaint procedure, jurisdiction, and `other`.
ISSUES = [
    'notice timing', 'notice content / topic specificity', 'acronyms and jargon',
    'discussion beyond the notice', 'votes and roll calls',
    'executive session: purpose', 'executive session: procedure',
    'executive session minutes', 'open session minutes', 'release of minutes',
    'remote participation', 'public access and recording', 'public comment',
]


def num_key(number):
    m = re.match(r'OML (\d{4})-(\d+)', number or '')
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def load():
    docs = []
    for p in sorted(glob.glob(os.path.join(DIGESTS, '*', '*.json'))):
        docs.append(json.load(open(p, encoding='utf-8')))
    if len(docs) < 2000:
        raise SystemExit('only %d digests under %s; refusing to rank a partial corpus' % (len(docs), DIGESTS))
    return docs


def build():
    docs = load()
    cited_by = {}
    for d in docs:
        for c in set(d.get('cites') or []):
            if c != d['number']:
                cited_by[c] = cited_by.get(c, 0) + 1
    texts = {}

    def letter(doc_id):
        if doc_id not in texts:
            p = os.path.join(TEXTS, doc_id + '.txt')
            texts[doc_id] = (re.sub(r'===page\d+===', '', L.squash(open(p, encoding='utf-8', errors='replace').read()))
                             if os.path.exists(p) else '')
        return texts[doc_id]

    # THE AG'S RECORD PER ISSUE: in how many letters it ruled against the body on that issue,
    # and in how many it ruled for it -- one count per letter per outcome. This is how much
    # precedent stands behind a point; oml_review.standout() weighs it.
    tally = {i: {'ruled_against': 0, 'ruled_for': 0, 'against_school_committees': 0} for i in ISSUES}
    for d in docs:
        hits = {}
        for a in d.get('allegations') or []:
            if a['issue'] in tally and a['holding'] in DECIDED:
                hits.setdefault(a['issue'], set()).add(a['holding'])
        for issue, hs in hits.items():
            if 'violation' in hs:
                tally[issue]['ruled_against'] += 1
                if d.get('body_type') in SCHOOL:
                    tally[issue]['against_school_committees'] += 1
            if 'no violation' in hs:
                tally[issue]['ruled_for'] += 1
    pool = {i: [] for i in ISSUES}
    rechecked = dropped = 0
    for d in docs:
        seen = set()
        for a in d.get('allegations') or []:
            if a['issue'] not in pool or a['holding'] not in DECIDED or a['issue'] in seen:
                continue
            kp = (a.get('key_passage') or '').strip()
            if len(kp) < MIN_PASSAGE or len(kp) > MAX_PASSAGE:
                continue
            rechecked += 1
            q = L.squash(kp)
            if len(q) < 20 or q not in letter(d['id']):
                dropped += 1
                continue
            seen.add(a['issue'])
            pool[a['issue']].append({
                'id': d['id'], 'number': d['number'], 'date': d['date'],
                'public_body': d['public_body'], 'body_type': d.get('body_type', ''),
                'holding': a['holding'], 'summary': a['summary'], 'key_passage': kp,
                'cited_by': cited_by.get(d['number'], 0),
                'text': os.path.relpath(os.path.join(TEXTS, d['id'] + '.txt'), ROOT),
                'publisher_filename': (d.get('source') or {}).get('publisher_filename', ''),
            })

    def by_cites(r):
        return (-r['cited_by'], tuple(-x for x in num_key(r['number'])))

    out = {}
    for issue in ISSUES:
        cands = sorted(pool[issue], key=by_cites)
        picks, why = [], {}

        def take(r, reason):
            if r and r['id'] not in why and len(picks) < PER_ISSUE:
                picks.append(r)
                why[r['id']] = reason

        for r in cands[:2]:
            take(r, 'most cited')
        take(next((r for r in cands if r['body_type'] in SCHOOL and r['id'] not in why), None),
             'most cited against a school committee')
        take(max(cands, key=lambda r: num_key(r['number'])) if cands else None, 'newest on this issue')
        held = {r['holding'] for r in picks}
        if len(held) == 1:
            other = (DECIDED - held).pop()
            take(next((r for r in cands if r['holding'] == other and r['id'] not in why), None),
                 'most cited with the other outcome')
        for r in cands:
            take(r, 'most cited')
        out[issue] = {'candidates': len(cands), 'record': tally[issue],
                      'rulings': [dict(r, why_picked=why[r['id']]) for r in picks]}
    return {
        'title': 'Leading Open Meeting Law rulings, per issue',
        'method': ('OURS, model-free. Ranked by how many later AG determinations cite each one; per issue: '
                   'the two most cited, the most cited against a school committee, the newest, the other '
                   'outcome if missing, then by citations. Decided on the merits only; each key passage '
                   're-checked verbatim against the letter. See scripts/build_oml_leading_rulings.py.'),
        'caution': ('A holding is the Attorney General’s reading of the law for ONE body on ONE set of '
                    'facts. It is not a finding about any other board.'),
        'corpus': {'determinations': len(docs), 'passages_rechecked': rechecked,
                   'passages_not_verbatim': dropped},
        'issues': out,
    }


def render(doc):
    return json.dumps(doc, ensure_ascii=False, indent=1) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render(build())
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE: %s does not reproduce; run scripts/build_oml_leading_rulings.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('oml-leading-rulings.json reproduces')
        return 0
    tmp = OUT + '.part'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    doc = json.loads(text)
    print('wrote %s: %d issues, %d rulings; %d passages rechecked, %d not verbatim'
          % (os.path.relpath(OUT, ROOT), len(doc['issues']),
             sum(len(v['rulings']) for v in doc['issues'].values()),
             doc['corpus']['passages_rechecked'], doc['corpus']['passages_not_verbatim']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
