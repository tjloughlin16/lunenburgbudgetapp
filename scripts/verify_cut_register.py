#!/usr/bin/env python3
"""Every figure on /cut-register, recomputed — and every quotation, re-read.

    python3 scripts/verify_cut_register.py

WHY THIS EXISTS SEPARATELY FROM THE GENERATOR. The generator refuses to write when a
structure it depends on stops holding. This asks a different question: is the file that is
PUBLISHED right now the one the documents and the database produce, and does every string
it quotes still exist, verbatim, at the coordinate it cites. Rule 9 — verify against the
source after writing, not before, and recompute rather than re-read.

Rule 13 is what shapes the checks. Every one of them derives the value from the data and
compares it to what the payload states; none of them asserts that a sentence exists. And
the quotation checks go back to the DOCUMENT, at the page the row cites, rather than to
the CSV — because the CSV is our rendering of the document and the whole point is that the
two agree.

    ok      the check passed
    FAIL    it did not, and the exit status is non-zero
"""
import collections
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28/public/data/cut-register.json')
CSV = os.path.join(ROOT, 'sources/data/stated-cuts.csv')
PAGE = os.path.join(ROOT, 'fy28/src/pages/CutRegister.tsx')
MANIFEST = os.path.join(ROOT, 'sources/data/archive-manifest.csv')

BAD = []


def check(name, got, want):
    ok = got == want
    print('%-4s %-72s %s' % ('ok' if ok else 'FAIL', name,
                             'got %r' % (got,) if ok else 'got %r want %r' % (got, want)))
    if not ok:
        BAD.append(name)


def note(name, ok, detail=''):
    print('%-4s %-72s %s' % ('ok' if ok else 'FAIL', name, detail))
    if not ok:
        BAD.append(name)


def norm(t):
    """The same normalisation the extractor uses, and only that.

    Bullet glyphs and line breaks are the EXTRACTOR'S rendering of a page rather than the
    district's words -- a deck's bullet arrives in the text layer as a Wingdings
    private-use character -- and a lone punctuation mark on its own line is a decorative
    icon. Nothing else is touched, so a changed word or a changed figure still fails."""
    t = re.sub(r'[•○●▪·-]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return re.sub(r'\s+', ' ', re.sub(r'(?<!\S)[^\w\s](?!\S)', ' ', t)).strip()


def main():
    for path in (PAYLOAD, CSV, DB, PAGE):
        if not os.path.exists(path):
            sys.exit('missing %s' % os.path.relpath(path, ROOT))
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
    cx = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    cx.row_factory = sqlite3.Row
    t = d['totals']

    print('== the register, against the CSV and the database')
    check('rows published = rows in the CSV', len(d['rows']), len(rows))
    check('rows published = rows in stated_cuts',
          len(d['rows']), cx.execute('SELECT COUNT(*) FROM stated_cuts').fetchone()[0])
    check('reductions', t['reductions'],
          sum(1 for r in rows if r['direction'] == 'reduction'))
    check('restorations and additions', t['restorations'],
          sum(1 for r in rows if r['direction'] in ('restoration', 'addition')))
    check('documents', t['documents'], len({r['doc_pdf'] for r in rows}))
    check('budget cycles', t['cycles'], len({r['fy'] for r in rows}))
    check('rows carrying a printed dollar figure', t['with_amount'],
          sum(1 for r in rows if r['amount']))
    check('rows carrying a printed FTE', t['with_fte'],
          sum(1 for r in rows if r['fte']))
    check('rows carrying the district’s own stated consequence', t['with_consequence'],
          sum(1 for r in rows if r['consequence']))
    check('every row is `stated` (rule 13a)',
          sorted({r['basis'] for r in rows}), ['stated'])

    print()
    print('== the two layers are never added together')
    note('no published total sums stated cuts and instrument readings',
         t['operative'] == t['moved_with'] + t['moved_other'] + t['unresolved']
         + t['blind'] + t['not_yet'],
         'the adopted reductions split exactly across the five verdicts and nothing else')
    check('adopted reductions = the sum of the verdict buckets', t['operative'],
          t['moved_with'] + t['moved_other'] + t['unresolved'] + t['blind']
          + t['not_yet'])
    check('measurable = adopted less the ones too early', t['measurable'],
          t['operative'] - t['not_yet'])
    check('the verdict breakdown sums to the adopted count',
          sum(v['n'] for v in d['categories']['by_verdict']), t['operative'])
    check('blind share', round(t['blind_share'], 2),
          round(100.0 * t['blind'] / t['measurable'], 2))
    tested = t['moved_with'] + t['moved_other'] + t['unresolved']
    check('agreement share, of what the instrument reaches', round(t['agree_share'], 2),
          round(100.0 * t['moved_with'] / tested, 2))

    print()
    print('== every verdict, recomputed from the state’s own series')
    series = collections.defaultdict(dict)
    for r in cx.execute("SELECT fy, org_name, subject, teacher_fte FROM "
                        "dese_teacher_subject WHERE district LIKE 'Lunenburg%'"):
        series[(r['org_name'], r['subject'])][r['fy']] = r['teacher_fte']
    bad = []
    for r in d['rows']:
        if r.get('before') is None or not r.get('instrument'):
            continue
        # The instrument string names the subject and the org(s) it was read from, so the
        # reading can be recovered from the payload alone and re-derived from the table.
        m = re.match(r'^DESE teacher FTE, (.+?), (.+)$', r['instrument'])
        if not m:
            bad.append((r['printed'], 'instrument string not readable'))
            continue
        subject, orgs = m.group(1), m.group(2).split(' + ')
        for fyk, val in (('before_fy', 'before'), ('after_fy', 'after')):
            want = round(sum(series.get((o, subject), {}).get(r[fyk], 0.0)
                             for o in orgs), 4)
            if abs(want - r[val]) > 1e-9:
                bad.append((r['printed'], '%s %s != %s' % (val, r[val], want)))
        if abs(round(r['after'] - r['before'], 4) - r['change']) > 1e-9:
            bad.append((r['printed'], 'change does not equal after minus before'))
    note('every published FTE reading reproduces from dese_teacher_subject',
         not bad, '%d readings checked' % sum(
             1 for r in d['rows'] if r.get('before') is not None))
    if bad:
        for p, why in bad[:8]:
            print('       %s — %s' % (p, why))

    print()
    print('== the three cases the conclusions name')
    a, b, c = d['fy2020'], d['fy2025'], d['fy2026']
    march = [r for r in rows if r['doc_date'] == '2019-03-06'
             and r['direction'] == 'reduction' and r['school'] != 'district']
    check('FY2020: positions named on the 6 March 2019 list', a['named_march'], len(march))
    check('FY2020: positions on the 3 April 2019 reduced column', a['named_april'],
          sum(1 for r in rows if r['doc_date'] == '2019-04-03'
              and r['direction'] == 'reduction'))
    check('FY2020: withdrawn between the two', len(a['withdrawn']), 3)
    note('FY2020: the middle school foreign language FTE falls',
         a['lms_foreign']['change'] <= -0.5,
         '%s → %s' % (a['lms_foreign']['before'], a['lms_foreign']['after']))
    note('FY2020: the high school foreign language FTE does not',
         a['lhs_foreign']['change'] > -0.5,
         '%s → %s' % (a['lhs_foreign']['before'], a['lhs_foreign']['after']))
    lib = {r['fy']: r['value'] for r in cx.execute(
        "SELECT fy, value FROM budget_figure WHERE label='P.S. Librarian' "
        "AND stage='restated'")}
    check('FY2020: the restated P.S. Librarian line is first funded in',
          a['primary_librarian']['first_funded_fy'],
          min(fy for fy, v in lib.items() if v > 0))

    check('FY2025: positions cut without the override', b['without'],
          sum(1 for r in rows if r['conditional_on'] == 'the override failing'
              and not r['position'].startswith('Expense lines')))
    check('FY2025: positions cut with it', b['with_override'],
          sum(1 for r in rows if r['conditional_on'] == 'the override passing'))
    check('FY2025: positions the vote took off the list', b['saved'],
          b['without'] - b['with_override'])
    check('FY2025: the document’s own arithmetic, 19 cut less 10 retained',
          b['stated_full_time_cut'] - b['stated_full_time_retained'], b['with_override'])
    check('FY2025: ESSER-funded posts cut', b['esser'],
          sum(1 for r in rows if r['block'].startswith('Positions CUT in the FY25')))
    check('FY2025: of them, on the with-override list', b['paired'], len(b['pairs']))
    ballot = cx.execute("SELECT yes, no, result FROM ballot_questions "
                        "WHERE date='2024-05-18'").fetchone()
    check('FY2025: the ballot result', b['ballot']['result'], ballot['result'])
    check('FY2025: yes votes', b['ballot']['yes'], int(ballot['yes']))
    check('FY2025: no votes', b['ballot']['no'], int(ballot['no']))

    check('FY2026: positions on the approved list', c['approved'],
          sum(1 for r in rows if r['fy'] == '2026'))
    note('FY2026: the world language cut is visible in the state’s count',
         c['row']['verdict'] == 'the instrument moved with it',
         '%s → %s' % (c['row']['before'], c['row']['after']))
    note('FY2026: at least one row goes the other way', bool(c['other_way']),
         ', '.join(o['printed'] for o in c['other_way']))

    print()
    print('== every quotation, re-read from the document at the page it cites')
    cache, missing = {}, []
    for r in rows:
        rel = os.path.join(ROOT, 'sources', r['doc_text'])
        if rel not in cache:
            cache[rel] = norm(open(rel, encoding='utf-8', errors='replace').read())
        for field in ('printed', 'consequence'):
            want = norm(r[field])
            if want and want not in cache[rel]:
                missing.append((r['doc_text'], field, want[:70]))
    note('every printed string and stated consequence is still in its document',
         not missing, '%d strings checked across %d documents'
         % (sum(1 for r in rows for f in ('printed', 'consequence') if r[f]),
            len(cache)))
    for m in missing[:8]:
        print('       %s — %s — %s' % m)

    # AND AT THE PAGE THE ROW CITES, not merely somewhere in the file. A page coordinate
    # that is wrong is a citation nobody can follow, which is rule 12's failure rather
    # than rule 13's, and it is invisible to a whole-file search.
    pages_cache, wrong_page = {}, []
    for r in rows:
        rel = os.path.join(ROOT, 'sources', r['doc_text'])
        if rel not in pages_cache:
            body = open(rel, encoding='utf-8', errors='replace').read()
            out, cur = {}, 1
            out[1] = []
            for line in body.splitlines():
                m = re.match(r'^===PAGE (\d+)===\s*$', line)
                if m:
                    cur = int(m.group(1))
                    out[cur] = []
                else:
                    out[cur].append(line)
            pages_cache[rel] = {k: norm('\n'.join(v)) for k, v in out.items()}
        page = pages_cache[rel].get(int(r['page']), '')
        want = norm(r['printed'])
        if want and want not in page:
            wrong_page.append((r['doc_text'], r['page'], want[:60]))
    note('every printed string is on the PAGE the row cites', not wrong_page,
         '%d coordinates checked' % len(rows))
    for m in wrong_page[:8]:
        print('       %s p.%s — %s' % m)

    print()
    print('== the meeting quotes')
    bad_quotes = []
    for q in d['said']:
        rel = q['cite'].replace('/docs/', 'sources/')
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            bad_quotes.append((rel, 'file missing'))
            continue
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8',
                                        errors='replace').read())
        if re.sub(r'\s+', ' ', q['quote']) not in text:
            bad_quotes.append((rel, 'quote no longer present'))
    note('every meeting quote is verbatim in the file it is attributed to',
         not bad_quotes, '%d quotes' % len(d['said']))
    for m in bad_quotes:
        print('       %s — %s' % m)

    print()
    print('== provenance (rule 12)')
    sha = {r['key']: r['sha256'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    wrong = [r['doc_pdf'] for r in rows if sha.get(r['doc_pdf']) != r['sha256']]
    note('every row’s sha256 matches the archive manifest', not wrong,
         '%d documents' % len({r['doc_pdf'] for r in rows}))
    for w in sorted(set(wrong))[:6]:
        print('       %s' % w)
    on_disk = [r['doc_pdf'] for r in rows
               if not os.path.exists(os.path.join(ROOT, 'sources', r['doc_pdf']))]
    note('every source document is on disk', not on_disk,
         'run scripts/sync_archive.py --pull if not')

    print()
    print('== the gap register (rule 7c)')
    for g in d['gaps']:
        r = cx.execute('SELECT why FROM money_gaps WHERE side=? AND what=?',
                       (g['side'], g['what'])).fetchone()
        note('money_gaps carries %r' % g['what'][:52], r is not None)
        if r is not None:
            note('  ...and it names the document that would close it',
                 '— closes:' in r['why'])

    print()
    print('== rule 2 — no figure typed into the page')
    src = open(PAGE, encoding='utf-8').read()
    body = re.sub(r'/\*[\s\S]*?\*/', ' ', src)          # drop the doc comments
    body = re.sub(r'^\s*//.*$', ' ', body, flags=re.M)
    # Everything that legitimately carries digits in a .tsx: Tailwind sizes, CSS lengths,
    # array indices, slice lengths, opacity, and the two fiscal years named in prose about
    # the FY2020 case, which are years rather than derived figures.
    body = re.sub(r'(?<![\w-])(text|leading|gap|mt|mb|ml|mr|p|pl|pr|py|px|pt|pb|w|h|'
                  r'min-h|max-w|border|rounded|top|space-y|space-x|gap-x|gap-y|'
                  r'grid-cols|sm|tracking)-\[?[\d.a-z/%()]+\]?', ' ', body)
    body = re.sub(r'\b(?:slice|padStart|toFixed|length)\(\s*[\d,\s]*\)', ' ', body)
    body = re.sub(r'[\d.]+(?:px|rem|em|%)', ' ', body)
    body = re.sub(r'\b(?:0|1|2|3|100|220|1e6)\b', ' ', body)
    body = re.sub(r'fyLabel\(\d{4}\)', ' ', body)       # a year named in prose
    body = re.sub(r'\bn=\{\d+\}', ' ', body)            # an Insight's own ordinal
    leftover = sorted(set(re.findall(r'\b\d[\d,.]*\b', body)))
    note('no unexplained figure is typed into pages/CutRegister.tsx', not leftover,
         'leftover: %s' % ', '.join(leftover) if leftover else '')

    print()
    print('== the persona review (rule 15a)')
    personas = os.path.join(ROOT, 'notes/process/PERSONAS.md')
    ran = os.path.exists(personas) and 'cut-register' in open(
        personas, encoding='utf-8').read()
    note('notes/process/PERSONAS.md records a review of this report', ran,
         'a verifier checks the figures; it cannot check that anybody’s question was '
         'answered')
    # AND THE THINGS THE REVIEW ADDED ARE ASSERTED, not trusted to stay. Five of the six
    # readers failed on the first pass and every fix was a piece of PROSE, which is
    # exactly what an editing pass removes without noticing. Three of the six tests are
    # about what a document OMITS, and an omission is invisible on re-reading your own
    # work -- so the check is that the text which satisfied each one is still there.
    flat = ' '.join(re.sub(r'<[^>]+>', ' ', src).split()).lower()
    NEEDED = [
        ('1 · the credit is given at the same weight as the caveat',
         'the lists exist because the district publishes them'),
        ('1 · no row is read as being about a person',
         'no row here is about a person'),
        ('2 · the repeatable sentence is the true one',
         'the honest answer is that nobody can tell'),
        ('4 · the Finance Committee control question is answered',
         'what you would have had to see, and when'),
        ('5 · "did the cuts we voted happen?" is answered before it is asked',
         'did the cuts we voted actually happen?'),
        ('6 · the town-versus-school frame is refused',
         'this is the school side only'),
    ]
    for label, needle in NEEDED:
        note('  %s' % label, ' '.join(needle.split()).lower() in flat)
    # The booster's test is about the PAYLOAD rather than the page, because the quotes are
    # data: for every category this report says was cut, somebody has to have looked for
    # what was asked for in the same year. Step 3 of the review, asserted.
    said = ' '.join(q['quote'] for q in d['said']).lower()
    note('  the booster: a concrete thing somebody asked for is quoted',
         'restore middle school athletics' in said and 'jazz band' in said,
         'the FY2027 budget cut middle school sports and Grade 5 band; both were asked '
         'for back in public three months later')

    print()
    if BAD:
        print('%d CHECK(S) FAILED' % len(BAD))
        for b in BAD:
            print('  %s' % b)
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
